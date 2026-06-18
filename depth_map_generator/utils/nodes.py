"""Node creation and management helpers for the depth map compositor pipeline."""

import os

import bpy


def remove_dm_nodes(tree):
    """Remove all nodes with the DM_ prefix from the node tree."""
    nodes_to_remove = [n for n in tree.nodes if n.name.startswith("DM_")]
    for node in nodes_to_remove:
        tree.nodes.remove(node)


def find_dm_node(tree, name):
    """Look up a DM_ prefixed node by name. Returns None if not found."""
    return tree.nodes.get(name)


def clear_all_nodes(tree):
    """Reset compositor to default RenderLayers -> Composite."""
    for node in tree.nodes:
        tree.nodes.remove(node)

    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers.location = (0, 0)

    composite = tree.nodes.new(type="CompositorNodeComposite")
    composite.location = (300, 0)

    tree.links.new(render_layers.outputs["Image"], composite.inputs["Image"])


def _apply_image_format(fmt, file_format, color_mode, bit_depth):
    """Apply format settings to an ImageFormatSettings struct.

    OpenEXR is the default: it stores raw float depth/matte data losslessly,
    unlike PNG/JPG which quantize to 8/16-bit integers and destroy precision.
    """
    fmt.file_format = file_format
    fmt.color_mode = color_mode
    fmt.color_depth = bit_depth
    if file_format == "OPEN_EXR":
        fmt.exr_codec = "ZIP"  # lossless
    elif file_format == "PNG":
        fmt.compression = 15


def configure_file_output(
    node, base_path, prefix, bit_depth="32", color_mode="BW", file_format="OPEN_EXR"
):
    """Centralized FileOutput node configuration.

    Args:
        node: CompositorNodeOutputFile node
        base_path: Absolute directory path for output
        prefix: Filename prefix (e.g. "depth_" or "depth_map")
        bit_depth: EXR float precision '16' (half) or '32' (full)
        color_mode: 'BW' or 'RGBA'
        file_format: 'OPEN_EXR' (default) or 'PNG'
    """
    # Ensure base_path ends with a separator so Blender treats it as a
    # directory, not a filename prefix.
    if base_path and not base_path.endswith(("/", "\\")):
        base_path = base_path + os.sep
    node.base_path = base_path
    _apply_image_format(node.format, file_format, color_mode, bit_depth)
    node.file_slots[0].path = prefix
    _apply_image_format(node.file_slots[0].format, file_format, color_mode, bit_depth)


def _create_render_layers(tree):
    """Create a fresh DM_RenderLayers node.

    Always creates a new node so its output sockets reflect the current
    view layer pass configuration (Depth, IndexOB, etc.). Existing
    RenderLayers nodes are left untouched to preserve user setups.
    """
    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers.name = "DM_RenderLayers"
    render_layers.label = "Depth Map Input"
    render_layers.location = (0, 0)
    return render_layers


def _append_range_contrast_ramp(tree, input_socket, settings, x_offset):
    """Append MapRange, Contrast, and ColorRamp nodes to the pipeline.

    Returns:
        tuple: (data_socket, preview_socket) where data_socket is the raw
            normalized MapRange output (for lossless file export) and
            preview_socket is the contrast/ColorRamp output (for viewing).
            The Contrast node applies a non-linear transform that destroys
            depth precision, so file output must tap the pre-contrast socket.
    """
    # MapRange node
    map_range = tree.nodes.new(type="CompositorNodeMapRange")
    map_range.name = "DM_RangeMapper"
    map_range.label = "Depth Range Adjuster"
    map_range.location = (x_offset, 0)

    if settings.use_custom_range:
        map_range.inputs["From Min"].default_value = settings.near_distance
        map_range.inputs["From Max"].default_value = settings.far_distance
    else:
        map_range.inputs["From Min"].default_value = 0.1
        map_range.inputs["From Max"].default_value = 1000.0

    # Invert output range for proper depth visualization
    map_range.inputs["To Min"].default_value = 1.0
    map_range.inputs["To Max"].default_value = 0.0

    tree.links.new(input_socket, map_range.inputs["Value"])

    # Contrast node
    contrast = tree.nodes.new(type="CompositorNodeBrightContrast")
    contrast.name = "DM_Contrast"
    contrast.label = "Enhance Depth Contrast"
    contrast.location = (x_offset + 200, 0)
    contrast.inputs["Contrast"].default_value = settings.contrast_value
    contrast.inputs["Bright"].default_value = settings.brightness_value
    tree.links.new(map_range.outputs["Value"], contrast.inputs["Image"])

    # ColorRamp node
    colorramp = tree.nodes.new(type="CompositorNodeValToRGB")
    colorramp.name = "DM_ColorRamp"
    colorramp.label = "Depth Visualization"
    colorramp.location = (x_offset + 400, 0)

    if len(colorramp.color_ramp.elements) > 1:
        colorramp.color_ramp.elements.remove(colorramp.color_ramp.elements[0])

    colorramp.color_ramp.elements[0].position = 0.0
    colorramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    newstop = colorramp.color_ramp.elements.new(1.0)
    newstop.color = (1.0, 1.0, 1.0, 1.0)

    tree.links.new(contrast.outputs["Image"], colorramp.inputs["Fac"])

    return map_range.outputs["Value"], colorramp.outputs[0]


def _create_linear_pipeline(tree, render_layers, settings):
    """LINEAR normalization: Depth -> MapRange(inverted) -> Contrast -> ColorRamp.

    Returns (data_socket, preview_socket).
    """
    return _append_range_contrast_ramp(tree, render_layers.outputs["Depth"], settings, 200)


def _create_logarithmic_pipeline(tree, render_layers, settings):
    """LOGARITHMIC normalization:
    Depth -> Multiply(scale) -> Log -> MapRange -> Contrast -> ColorRamp.

    Returns (data_socket, preview_socket).
    """

    # Scale factor multiply
    multiply = tree.nodes.new(type="CompositorNodeMath")
    multiply.name = "DM_ScaleMultiply"
    multiply.label = "Depth Scale"
    multiply.location = (200, 0)
    multiply.operation = "MULTIPLY"
    multiply.inputs[1].default_value = settings.depth_scale_factor
    tree.links.new(render_layers.outputs["Depth"], multiply.inputs[0])

    # Logarithm node
    log_node = tree.nodes.new(type="CompositorNodeMath")
    log_node.name = "DM_Logarithm"
    log_node.label = "Logarithmic Depth"
    log_node.location = (400, 0)
    log_node.operation = "LOGARITHM"
    log_node.inputs[1].default_value = 10.0
    tree.links.new(multiply.outputs["Value"], log_node.inputs[0])

    return _append_range_contrast_ramp(tree, log_node.outputs["Value"], settings, 600)


def _create_raw_pipeline(tree, render_layers, settings):
    """RAW normalization:
    Depth -> Multiply(scale) -> Contrast (preview only).

    Returns (data_socket, preview_socket). data_socket is the scaled depth
    before the Contrast transform, so file export keeps raw values.
    """

    # Scale factor multiply
    multiply = tree.nodes.new(type="CompositorNodeMath")
    multiply.name = "DM_ScaleMultiply"
    multiply.label = "Depth Scale"
    multiply.location = (200, 0)
    multiply.operation = "MULTIPLY"
    multiply.inputs[1].default_value = settings.depth_scale_factor
    tree.links.new(render_layers.outputs["Depth"], multiply.inputs[0])

    # Contrast node
    contrast = tree.nodes.new(type="CompositorNodeBrightContrast")
    contrast.name = "DM_Contrast"
    contrast.label = "Enhance Depth Contrast"
    contrast.location = (400, 0)
    contrast.inputs["Contrast"].default_value = settings.contrast_value
    contrast.inputs["Bright"].default_value = settings.brightness_value
    tree.links.new(multiply.outputs["Value"], contrast.inputs["Image"])

    return multiply.outputs["Value"], contrast.outputs["Image"]


def create_depth_pipeline(tree, settings, prefs=None):
    """Build the full depth map compositor pipeline based on normalization mode.

    Args:
        tree: The compositor node tree
        settings: DepthMapSettings property group
        prefs: AddonPreferences (optional, for default paths)

    Returns:
        tuple: (render_layers_node, data_socket, preview_socket)
    """
    render_layers = _create_render_layers(tree)

    normalization = settings.depth_normalization
    if normalization == "LOGARITHMIC":
        data_socket, preview_socket = _create_logarithmic_pipeline(tree, render_layers, settings)
    elif normalization == "RAW":
        data_socket, preview_socket = _create_raw_pipeline(tree, render_layers, settings)
    else:  # LINEAR (default)
        data_socket, preview_socket = _create_linear_pipeline(tree, render_layers, settings)

    return render_layers, data_socket, preview_socket


def _get_output_x_offset(normalization):
    """Get the X offset for output nodes based on pipeline length."""
    if normalization == "LOGARITHMIC":
        return 1200
    elif normalization == "RAW":
        return 600
    return 800  # LINEAR


def create_output_nodes(tree, settings, data_socket, preview_socket, prefs=None):
    """Create output nodes (Composite, Viewer, FileOutput) based on settings.

    Args:
        tree: The compositor node tree
        settings: DepthMapSettings property group
        data_socket: Raw normalized depth socket (lossless, for file export)
        preview_socket: Contrast/ColorRamp socket (for Composite/Viewer display)
        prefs: AddonPreferences (optional)
    """
    from . import paths

    x_offset = _get_output_x_offset(settings.depth_normalization)
    bit_depth = settings.output_bit_depth

    # Always create Composite node (uses the visual preview socket)
    composite = tree.nodes.new(type="CompositorNodeComposite")
    composite.name = "DM_Composite"
    composite.label = "Depth Map Output"
    composite.location = (x_offset, -100)
    tree.links.new(preview_socket, composite.inputs["Image"])

    if settings.depth_output_method == "COMPOSITE":
        composite.location = (x_offset, 0)

    elif settings.depth_output_method == "VIEWER":
        viewer = tree.nodes.new(type="CompositorNodeViewer")
        viewer.name = "DM_Viewer"
        viewer.label = "Depth Preview"
        viewer.location = (x_offset, 50)
        tree.links.new(preview_socket, viewer.inputs["Image"])

    elif settings.depth_output_method == "FILE_OUTPUT":
        output_dir = paths.get_depth_output_dir(settings, prefs)
        paths.resolve_output_path(output_dir, create=True, prefs=prefs)

        file_output = tree.nodes.new(type="CompositorNodeOutputFile")
        file_output.name = "DM_FileOutput"
        file_output.label = "Depth Map Files"
        file_output.location = (x_offset, 100)

        prefix = "depth_" if settings.render_animation else "depth_map"
        # File export taps the raw normalized socket — no Contrast distortion.
        configure_file_output(file_output, output_dir, prefix, bit_depth=bit_depth, color_mode="BW")

        tree.links.new(data_socket, file_output.inputs[0])

    # Optional preview viewer alongside file output
    if settings.preview_before_export and settings.depth_output_method == "FILE_OUTPUT":
        viewer = tree.nodes.new(type="CompositorNodeViewer")
        viewer.name = "DM_Viewer"
        viewer.label = "Depth Preview"
        viewer.location = (x_offset, 200)
        tree.links.new(preview_socket, viewer.inputs["Image"])


def _configure_cryptomatte(crypto, view_layer, settings):
    """Point a CryptomatteV2 node at the scene's object crypto layer.

    The layer_name enum uses 'ViewLayer.CryptoObject' form; setting it to a
    bad value raises 'enum not found', so we resolve a valid identifier at
    runtime. matte_id is the exact object name (Cryptomatte matches by name,
    not pass index).
    """
    crypto.source = "RENDER"
    crypto.scene = bpy.context.scene

    desired = f"{view_layer.name}.CryptoObject"
    prop = crypto.bl_rna.properties.get("layer_name")
    valid = [item.identifier for item in prop.enum_items] if prop else []
    if desired in valid:
        crypto.layer_name = desired
    elif valid:
        # Fall back to the first CryptoObject layer Blender exposes.
        crypto.layer_name = next((v for v in valid if "CryptoObject" in v), valid[0])

    if settings.mask_object:
        crypto.matte_id = settings.mask_object.name


def create_mask_pipeline(tree, settings, prefs=None):
    """Build the alpha mask compositor pipeline.

    Creates its own DM_MaskRenderLayers node to guarantee that
    IndexOB / Cryptomatte outputs are available (independent of the
    depth pipeline's RenderLayers node).

    Args:
        tree: The compositor node tree
        settings: DepthMapSettings property group
        prefs: AddonPreferences (optional)
    """
    from . import paths

    if settings.mask_source == "OBJECT_INDEX":
        # Ensure pass is enabled before creating the node
        view_layer = bpy.context.view_layer
        view_layer.use_pass_object_index = True

        # Create a dedicated RenderLayers node for the mask pipeline
        mask_rl = tree.nodes.new(type="CompositorNodeRLayers")
        mask_rl.name = "DM_MaskRenderLayers"
        mask_rl.label = "Mask Input"
        mask_rl.location = (0, -300)

        # Assign view layer and force depsgraph update so the node
        # rebuilds its sockets with the newly enabled IndexOB pass
        mask_rl.layer = view_layer.name
        bpy.context.scene.update_tag()
        bpy.context.evaluated_depsgraph_get().update()

        # Find IndexOB socket by iteration — the 'in' operator on
        # bpy_prop_collection can fail for pass sockets even when
        # the socket exists, because it uses internal key lookup
        # that may not reflect recently enabled passes.
        index_ob = next((s for s in mask_rl.outputs if s.name == "IndexOB"), None)
        if index_ob is None:
            available = [s.name for s in mask_rl.outputs]
            raise RuntimeError(
                "IndexOB output not found on RenderLayers node. "
                f"Available outputs: {available}. "
                "Enable 'Object Index Pass' on the view layer "
                "(Properties > View Layer > Passes > Data)."
            )

        # IndexOB -> Compare(mask_index) -> FileOutput
        compare = tree.nodes.new(type="CompositorNodeMath")
        compare.name = "DM_MaskCompare"
        compare.label = "Mask Index Compare"
        compare.location = (200, -300)
        compare.operation = "COMPARE"
        compare.inputs[1].default_value = float(settings.mask_index)
        compare.inputs[2].default_value = 0.5  # epsilon
        tree.links.new(index_ob, compare.inputs[0])
        mask_output_socket = compare.outputs["Value"]

    elif settings.mask_source == "CRYPTOMATTE":
        if bpy.app.version < (3, 2, 0):
            raise RuntimeError("CryptomatteV2 requires Blender 3.2 or newer.")

        # Enable the Cryptomatte object pass so the engine (Eevee Next or
        # Cycles) writes the required Crypto AOV during rendering.
        view_layer = bpy.context.view_layer
        view_layer.use_pass_cryptomatte_object = True
        if hasattr(view_layer, "use_pass_cryptomatte_accurate"):
            view_layer.use_pass_cryptomatte_accurate = True  # sub-pixel accuracy
        view_layer.pass_cryptomatte_depth = 6  # max objects per pixel
        bpy.context.scene.update_tag()
        bpy.context.evaluated_depsgraph_get().update()

        # Cryptomatte node
        crypto = tree.nodes.new(type="CompositorNodeCryptomatteV2")
        crypto.name = "DM_Cryptomatte"
        crypto.label = "Object Mask (Cryptomatte)"
        crypto.location = (200, -300)
        _configure_cryptomatte(crypto, view_layer, settings)
        mask_output_socket = crypto.outputs["Matte"]

    else:
        return

    # Create mask file output
    output_dir = paths.get_mask_output_dir(settings, prefs)
    paths.resolve_output_path(output_dir, create=True, prefs=prefs)

    mask_file_output = tree.nodes.new(type="CompositorNodeOutputFile")
    mask_file_output.name = "DM_MaskFileOutput"
    mask_file_output.label = "Mask Map Files"
    mask_file_output.location = (400, -300)

    color_mode = "RGBA" if settings.mask_output_format == "RGBA_PNG" else "BW"
    prefix = "mask_" if settings.render_animation else "mask_map"
    # Masks are binary coverage — 16-bit half EXR is ample and smaller on disk.
    configure_file_output(
        mask_file_output,
        output_dir,
        prefix,
        bit_depth="16",
        color_mode=color_mode,
    )

    tree.links.new(mask_output_socket, mask_file_output.inputs[0])


def update_depth_nodes(tree, settings, prefs=None):
    """Update existing depth pipeline nodes without recreating them.

    Returns True if update succeeded, False if rebuild is needed.
    """
    range_node = find_dm_node(tree, "DM_RangeMapper")
    if range_node:
        if settings.use_custom_range:
            range_node.inputs["From Min"].default_value = settings.near_distance
            range_node.inputs["From Max"].default_value = settings.far_distance
        else:
            range_node.inputs["From Min"].default_value = 0.1
            range_node.inputs["From Max"].default_value = 1000.0
        range_node.inputs["To Min"].default_value = 1.0
        range_node.inputs["To Max"].default_value = 0.0

    contrast_node = find_dm_node(tree, "DM_Contrast")
    if contrast_node:
        contrast_node.inputs["Contrast"].default_value = settings.contrast_value
        contrast_node.inputs["Bright"].default_value = settings.brightness_value

    scale_node = find_dm_node(tree, "DM_ScaleMultiply")
    if scale_node:
        scale_node.inputs[1].default_value = settings.depth_scale_factor

    ramp_node = find_dm_node(tree, "DM_ColorRamp")
    if settings.depth_normalization != "RAW" and not ramp_node:
        return False

    # Update file output path
    from . import paths

    file_output = find_dm_node(tree, "DM_FileOutput")
    if file_output and settings.depth_output_method == "FILE_OUTPUT":
        output_dir = paths.get_depth_output_dir(settings, prefs)
        paths.resolve_output_path(output_dir, create=True, prefs=prefs)
        prefix = "depth_" if settings.render_animation else "depth_map"

        source_socket = None
        if file_output.inputs[0].links:
            source_socket = file_output.inputs[0].links[0].from_socket

        configure_file_output(
            file_output, output_dir, prefix, bit_depth=settings.output_bit_depth, color_mode="BW"
        )

        if source_socket and not file_output.inputs[0].links:
            tree.links.new(source_socket, file_output.inputs[0])

    # Update or create mask pipeline
    mask_file_output = find_dm_node(tree, "DM_MaskFileOutput")
    if settings.mask_enabled:
        # Detect mask source mismatch (e.g. user switched from Object Index to
        # Cryptomatte). The existing pipeline nodes are incompatible, so remove
        # them and rebuild from scratch.
        source_mismatch = False
        if settings.mask_source == "OBJECT_INDEX" and find_dm_node(tree, "DM_Cryptomatte"):
            source_mismatch = True
        elif settings.mask_source == "CRYPTOMATTE" and find_dm_node(tree, "DM_MaskCompare"):
            source_mismatch = True

        if source_mismatch:
            for name in (
                "DM_MaskFileOutput",
                "DM_MaskRenderLayers",
                "DM_MaskCompare",
                "DM_Cryptomatte",
            ):
                node = find_dm_node(tree, name)
                if node:
                    tree.nodes.remove(node)
            create_mask_pipeline(tree, settings, prefs)
            return True

        if mask_file_output:
            # Update existing mask file output path
            mask_output_dir = paths.get_mask_output_dir(settings, prefs)
            paths.resolve_output_path(mask_output_dir, create=True, prefs=prefs)
            color_mode = "RGBA" if settings.mask_output_format == "RGBA_PNG" else "BW"
            prefix = "mask_" if settings.render_animation else "mask_map"

            source_socket = None
            if mask_file_output.inputs[0].links:
                source_socket = mask_file_output.inputs[0].links[0].from_socket

            configure_file_output(
                mask_file_output,
                mask_output_dir,
                prefix,
                bit_depth="16",
                color_mode=color_mode,
            )

            if source_socket and not mask_file_output.inputs[0].links:
                tree.links.new(source_socket, mask_file_output.inputs[0])

            # Sync mask index threshold to comparator node
            compare_node = find_dm_node(tree, "DM_MaskCompare")
            if compare_node:
                compare_node.inputs[1].default_value = float(settings.mask_index)

            # Sync Cryptomatte target object (matched by name) to the node
            crypto_node = find_dm_node(tree, "DM_Cryptomatte")
            if crypto_node:
                _configure_cryptomatte(crypto_node, bpy.context.view_layer, settings)

        else:
            # Mask was enabled after initial setup — create the pipeline now.
            # Errors are intentionally not caught here so the caller (setup
            # operator) can report them to the user.
            create_mask_pipeline(tree, settings, prefs)
    elif mask_file_output:
        # Mask was disabled after setup — remove stale mask pipeline nodes
        for name in (
            "DM_MaskFileOutput",
            "DM_MaskRenderLayers",
            "DM_MaskCompare",
            "DM_Cryptomatte",
        ):
            node = find_dm_node(tree, name)
            if node:
                tree.nodes.remove(node)

    return True
