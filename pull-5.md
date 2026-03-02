Code Review
This pull request is a significant and well-structured refactoring of the addon into a modular package, which greatly improves maintainability. The new features like normalization modes and mask exporting are valuable additions. My review focuses on a few areas to improve robustness and correct some minor bugs, particularly around path handling with addon preferences and ensuring user compositor setups are preserved, in line with the repository's style guide.

depth_map_generator/operators/mask_export.py
Comment on lines +22 to +73
    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings
            tree = scene.node_tree

            # Validate Cryptomatte requires Cycles
            if (settings.mask_source == 'CRYPTOMATTE'
                    and scene.render.engine != 'CYCLES'):
                self.report(
                    {'ERROR'},
                    "Cryptomatte requires Cycles render engine. "
                    "Switch to Cycles or use Object Index mode."
                )
                return {'CANCELLED'}

            # Ensure mask pipeline exists
            mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")
            if not mask_node:
                # Rebuild mask pipeline
                render_layers = nodes.find_dm_node(tree, "DM_RenderLayers")
                if not render_layers:
                    self.report({'ERROR'}, "Run Setup first")
                    return {'CANCELLED'}

                prefs = context.preferences.addons.get("depth_map_generator")
                prefs = prefs.preferences if prefs else None
                nodes.create_mask_pipeline(tree, render_layers, settings, prefs)

            # Render
            if (settings.depth_output_method == 'FILE_OUTPUT'
                    and settings.render_animation):
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                output_dir = paths.get_mask_output_dir(settings)
                self.report(
                    {'INFO'},
                    f"Exporting mask animation: {frame_count} frames to {output_dir}"
                )
                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            else:
                self.report({'INFO'}, "Exporting single mask frame")
                bpy.ops.render.render('INVOKE_DEFAULT')

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Mask export failed: {str(e)}")
            return {'CANCELLED'}
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
high

This method has a couple of issues:

The prefs variable is initialized in a limited scope and not passed to get_mask_output_dir, preventing user preferences for default paths from being used.
The condition for rendering an animation (if (settings.depth_output_method == 'FILE_OUTPUT' and settings.render_animation)) is too restrictive. Mask animations should be exportable regardless of the depth map output setting.
The suggested change moves prefs initialization to the top of the method, uses it when getting the output directory, and simplifies the animation condition. You'll also need to update the corresponding UI in panels/mask_panel.py.

    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings
            tree = scene.node_tree
            prefs = context.preferences.addons.get("depth_map_generator")
            prefs = prefs.preferences if prefs else None

            # Validate Cryptomatte requires Cycles
            if (settings.mask_source == 'CRYPTOMATTE'
                    and scene.render.engine != 'CYCLES'):
                self.report(
                    {'ERROR'},
                    "Cryptomatte requires Cycles render engine. "
                    "Switch to Cycles or use Object Index mode."
                )
                return {'CANCELLED'}

            # Ensure mask pipeline exists
            mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")
            if not mask_node:
                # Rebuild mask pipeline
                render_layers = nodes.find_dm_node(tree, "DM_RenderLayers")
                if not render_layers:
                    self.report({'ERROR'}, "Run Setup first")
                    return {'CANCELLED'}

                nodes.create_mask_pipeline(tree, render_layers, settings, prefs)

            # Render
            if settings.render_animation:
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                output_dir = paths.get_mask_output_dir(settings, prefs)
                self.report(
                    {'INFO'},
                    f"Exporting mask animation: {frame_count} frames to {output_dir}"
                )
                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            else:
                self.report({'INFO'}, "Exporting single mask frame")
                bpy.ops.render.render('INVOKE_DEFAULT')

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Mask export failed: {str(e)}")
            return {'CANCELLED'}
@Limbicnation Reply...
depth_map_generator/operators/render.py
Comment on lines +16 to +48
    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings

            # Auto-setup if not already configured
            if not settings.setup_complete:
                bpy.ops.depthmap.setup()

            if (settings.depth_output_method == 'FILE_OUTPUT'
                    and settings.render_animation):
                # Set custom frame range if not using scene range
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                output_dir = paths.get_depth_output_dir(settings)
                self.report(
                    {'INFO'},
                    f"Rendering depth animation: {frame_count} frames to {output_dir}"
                )

                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            else:
                self.report({'INFO'}, "Rendering single depth map frame")
                bpy.ops.render.render('INVOKE_DEFAULT')

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Render failed: {str(e)}")
            return {'CANCELLED'}
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
high

The addon preferences (prefs) are not being fetched in this method. As a result, the call to paths.get_depth_output_dir on line 33 doesn't receive them, and the user's default output path setting from preferences will be ignored. You should fetch prefs at the beginning of the method and pass it to get_depth_output_dir.

    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings
            prefs = context.preferences.addons.get("depth_map_generator")
            prefs = prefs.preferences if prefs else None

            # Auto-setup if not already configured
            if not settings.setup_complete:
                bpy.ops.depthmap.setup()

            if (settings.depth_output_method == 'FILE_OUTPUT'
                    and settings.render_animation):
                # Set custom frame range if not using scene range
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                output_dir = paths.get_depth_output_dir(settings, prefs)
                self.report(
                    {'INFO'},
                    f"Rendering depth animation: {frame_count} frames to {output_dir}"
                )

                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            else:
                self.report({'INFO'}, "Rendering single depth map frame")
                bpy.ops.render.render('INVOKE_DEFAULT')

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Render failed: {str(e)}")
            return {'CANCELLED'}
@Limbicnation Reply...
depth_map_generator/operators/setup.py
Comment on lines +40 to +41
                for node in tree.nodes:
                    tree.nodes.remove(node)
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
high

Clearing all nodes from the compositor tree during a fresh setup is a destructive action that can erase a user's custom node setup. This violates the style guide's principle to "preserves existing setups when possible". Instead of clearing all nodes, you should specifically remove only the nodes created by this addon, which can be identified by the "DM_" prefix.

                nodes.remove_dm_nodes(tree)
References
@Limbicnation Reply...
depth_map_generator/utils/nodes.py
Comment on lines +358 to +400
def update_depth_nodes(tree, settings):
    """Update existing depth pipeline nodes without recreating them.

    Returns True if update succeeded, False if rebuild is needed.
    """
    range_node = find_dm_node(tree, "DM_RangeMapper")
    if range_node:
        if settings.use_custom_range:
            range_node.inputs['From Min'].default_value = settings.near_distance
            range_node.inputs['From Max'].default_value = settings.far_distance
        else:
            range_node.inputs['From Min'].default_value = 0.1
            range_node.inputs['From Max'].default_value = 1000.0
        range_node.inputs['To Min'].default_value = 1.0
        range_node.inputs['To Max'].default_value = 0.0

    contrast_node = find_dm_node(tree, "DM_Contrast")
    if contrast_node:
        contrast_node.inputs['Contrast'].default_value = settings.contrast_value
        contrast_node.inputs['Bright'].default_value = settings.brightness_value

    scale_node = find_dm_node(tree, "DM_ScaleMultiply")
    if scale_node:
        scale_node.inputs[1].default_value = settings.depth_scale_factor

    ramp_node = find_dm_node(tree, "DM_ColorRamp")
    if settings.depth_normalization != 'RAW' and not ramp_node:
        return False

    # Update file output path
    from . import paths
    file_output = find_dm_node(tree, "DM_FileOutput")
    if file_output and settings.depth_output_method == 'FILE_OUTPUT':
        output_dir = paths.get_depth_output_dir(settings)
        paths.resolve_output_path(output_dir, create=True)
        prefix = "depth_" if settings.render_animation else "depth_map"
        configure_file_output(
            file_output, output_dir, prefix,
            bit_depth=settings.output_bit_depth, color_mode='BW',
            is_anim=settings.render_animation
        )

    return True
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
high

The update_depth_nodes function doesn't account for addon preferences when updating file output paths because the prefs object is not passed to it. This can result in the wrong output directory being used when settings are updated.

I've updated the function to accept and use prefs. You will also need to update the call to this function in operators/setup.py to pass the prefs object: nodes.update_depth_nodes(tree, settings, prefs).

def update_depth_nodes(tree, settings, prefs=None):
    """Update existing depth pipeline nodes without recreating them.

    Returns True if update succeeded, False if rebuild is needed.
    """
    range_node = find_dm_node(tree, "DM_RangeMapper")
    if range_node:
        if settings.use_custom_range:
            range_node.inputs['From Min'].default_value = settings.near_distance
            range_node.inputs['From Max'].default_value = settings.far_distance
        else:
            range_node.inputs['From Min'].default_value = 0.1
            range_node.inputs['From Max'].default_value = 1000.0
        range_node.inputs['To Min'].default_value = 1.0
        range_node.inputs['To Max'].default_value = 0.0

    contrast_node = find_dm_node(tree, "DM_Contrast")
    if contrast_node:
        contrast_node.inputs['Contrast'].default_value = settings.contrast_value
        contrast_node.inputs['Bright'].default_value = settings.brightness_value

    scale_node = find_dm_node(tree, "DM_ScaleMultiply")
    if scale_node:
        scale_node.inputs[1].default_value = settings.depth_scale_factor

    ramp_node = find_dm_node(tree, "DM_ColorRamp")
    if settings.depth_normalization != 'RAW' and not ramp_node:
        return False

    # Update file output path
    from . import paths
    file_output = find_dm_node(tree, "DM_FileOutput")
    if file_output and settings.depth_output_method == 'FILE_OUTPUT':
        output_dir = paths.get_depth_output_dir(settings, prefs)
        paths.resolve_output_path(output_dir, create=True)
        prefix = "depth_" if settings.render_animation else "depth_map"
        configure_file_output(
            file_output, output_dir, prefix,
            bit_depth=settings.output_bit_depth, color_mode='BW',
            is_anim=settings.render_animation
        )

    return True
@Limbicnation Reply...
depth_map_generator/operators/reset.py

            # Reset compositor to default
            if scene.use_nodes:
                nodes.clear_all_nodes(scene.node_tree)
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
medium

Using clear_all_nodes is a destructive action that removes all nodes from the compositor, not just the ones created by this addon. This can lead to unintended data loss for users with existing node setups. To better align with the style guide's principle of preserving existing setups, consider using a more targeted cleanup function like nodes.remove_dm_nodes.

Suggested change
                nodes.clear_all_nodes(scene.node_tree)
                nodes.remove_dm_nodes(scene.node_tree)
References
@Limbicnation Reply...
depth_map_generator/panels/mask_panel.py
Comment on lines +50 to +51
        if (settings.depth_output_method == 'FILE_OUTPUT'
                and settings.render_animation):
@gemini-code-assist
gemini-code-assist bot
2 minutes ago
medium

This condition for showing the "Export Mask Animation" button is tied to settings.depth_output_method == 'FILE_OUTPUT'. This is unnecessarily restrictive, as mask export should be possible even if the depth map is being sent to the Viewer. To align with the suggested logic change in the depthmap.export_mask operator, this should only depend on settings.render_animation.

        if settings.render_animation:
