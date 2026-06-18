"""Mask export operator - renders alpha mask for ComfyUI workflows."""

import os

import bpy
from bpy.types import Operator

from ..utils import nodes, paths

# Node names that make up the mask pipeline. Used for stale-node cleanup
# so a partial prior build cannot leave duplicate RenderLayers behind.
_MASK_NODE_NAMES = (
    "DM_MaskRenderLayers",
    "DM_MaskCompare",
    "DM_MaskFileOutput",
    "DM_Cryptomatte",
)


class DEPTHMAP_OT_export_mask(Operator):
    """Exports an alpha mask using Object Index or Cryptomatte."""

    bl_idname = "depthmap.export_mask"
    bl_label = "Export Mask"
    bl_description = "Render and export an alpha mask for the selected objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        settings = context.scene.depth_map_settings
        return settings.mask_enabled and settings.setup_complete

    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings
            tree = scene.node_tree
            view_layer = context.view_layer
            prefs_addon = context.preferences.addons.get("depth_map_generator")
            prefs = prefs_addon.preferences if prefs_addon else None

            # Cryptomatte is Cycles-only.
            if settings.mask_source == "CRYPTOMATTE" and scene.render.engine != "CYCLES":
                self.report(
                    {"ERROR"},
                    "Cryptomatte requires Cycles render engine. "
                    "Switch to Cycles or use Object Index mode.",
                )
                return {"CANCELLED"}

            # Explicitly enable the Object Index pass *before* we look for or
            # build the mask pipeline. create_mask_pipeline() also does this,
            # but enabling here guarantees the pass is on even when the pipeline
            # node already exists from a setup that ran with mask disabled.
            if settings.mask_source == "OBJECT_INDEX":
                view_layer.use_pass_object_index = True
                scene.update_tag()
                context.evaluated_depsgraph_get().update()

            # Ensure the mask pipeline exists. If DM_MaskFileOutput is missing,
            # a previous build may have partially failed and left orphan nodes
            # (e.g. DM_MaskRenderLayers without its FileOutput). Remove all mask
            # nodes first so create_mask_pipeline() cannot create duplicates.
            mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")
            if not mask_node:
                for name in _MASK_NODE_NAMES:
                    stale = nodes.find_dm_node(tree, name)
                    if stale:
                        tree.nodes.remove(stale)

                nodes.create_mask_pipeline(tree, settings, prefs)
                mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")

            # Validate the mask FileOutput is actually connected to the pipeline.
            if not mask_node or not mask_node.inputs[0].links:
                self.report(
                    {"ERROR"},
                    "Mask pipeline is not connected. "
                    "Try 'Reset Compositing' then 'Setup Depth Map' with mask enabled.",
                )
                return {"CANCELLED"}

            # Validate and create output directory before committing to a render.
            output_dir = paths.get_mask_output_dir(settings, prefs)
            is_valid, error_msg = paths.validate_output_path(output_dir)
            if not is_valid:
                self.report({"ERROR"}, f"Invalid mask output path: {error_msg}")
                return {"CANCELLED"}

            # Ensure the directory exists. create_mask_pipeline() creates it
            # during a fresh build, but when the pipeline already exists and
            # the user changed mask_output_path after setup, the new directory
            # is never created — and Blender's FileOutput silently fails.
            paths.resolve_output_path(output_dir, create=True, prefs=prefs)

            # Verify the upstream link (IndexOB -> DM_MaskCompare) is intact.
            # Blender severs this link when the Object Index pass is toggled
            # off and on again, because the IndexOB socket is destroyed and
            # recreated. The existing check at line 75 only validates the
            # FileOutput connection, not this upstream link.
            if settings.mask_source == "OBJECT_INDEX":
                self._ensure_index_ob_link(tree, view_layer, scene, context)

            # Re-sync the FileOutput to the current settings. The node keeps the
            # base_path it was given when the pipeline was built, so if an
            # earlier setup used a different output path/format the node would
            # still write there — and _verify_mask_output would look in the new
            # path and falsely report "no mask files found". Reconfiguring is
            # idempotent and makes the output land where the user expects.
            color_mode = "RGBA" if settings.mask_output_format == "RGBA_PNG" else "BW"
            prefix = "mask_" if settings.render_animation else "mask_map"

            source_socket = None
            if mask_node.inputs[0].links:
                source_socket = mask_node.inputs[0].links[0].from_socket

            nodes.configure_file_output(
                mask_node,
                output_dir,
                prefix,
                bit_depth=settings.output_bit_depth,
                color_mode=color_mode,
            )

            if source_socket and not mask_node.inputs[0].links:
                tree.links.new(source_socket, mask_node.inputs[0])

            # Render. Mask animation is independent of depth output method.
            # Single-frame uses EXEC_DEFAULT (blocking) so we can verify the
            # FileOutput actually wrote files before reporting success.
            # Animations stay non-blocking to avoid freezing the UI.
            if settings.render_animation:
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                self.report(
                    {"INFO"},
                    f"Exporting mask animation: {frame_count} frames to {output_dir}",
                )
                bpy.ops.render.render("INVOKE_DEFAULT", animation=True)
            else:
                self.report({"INFO"}, "Exporting single mask frame")
                bpy.ops.render.render("EXEC_DEFAULT")
                self._verify_mask_output(output_dir)

            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Mask export failed: {str(e)}")
            return {"CANCELLED"}

    def _verify_mask_output(self, output_dir):
        """Warn if no mask PNG was written after a blocking render.

        Reports an ERROR (not just WARNING) when the output directory does not
        exist, since this means the FileOutput node had nowhere to write.
        """
        abs_dir = bpy.path.abspath(output_dir)
        if not os.path.isdir(abs_dir):
            self.report(
                {"ERROR"},
                f"Output directory does not exist: {abs_dir}. Check the mask output path setting.",
            )
            return
        png_files = [
            f for f in os.listdir(abs_dir) if f.lower().endswith(".png") and "mask" in f.lower()
        ]
        if not png_files:
            self.report(
                {"WARNING"},
                f"Render completed but no mask files found in {abs_dir}. "
                "Check compositor node connections and object Pass Index values.",
            )

    @staticmethod
    def _ensure_index_ob_link(tree, view_layer, scene, context):
        """Restore the IndexOB -> DM_MaskCompare link if Blender severed it.

        Blender destroys the IndexOB socket (and all links to it) on a
        CompositorNodeRLayers node when use_pass_object_index is toggled off.
        Re-enabling the pass recreates the socket but does NOT restore the
        link. This method detects the gap and reconnects.
        """
        mask_rl = nodes.find_dm_node(tree, "DM_MaskRenderLayers")
        compare = nodes.find_dm_node(tree, "DM_MaskCompare")
        if not mask_rl or not compare:
            return

        index_ob = next((s for s in mask_rl.outputs if s.name == "IndexOB"), None)
        if index_ob is None:
            # Socket not yet available — force a depsgraph rebuild.
            mask_rl.layer = view_layer.name
            scene.update_tag()
            context.evaluated_depsgraph_get().update()
            index_ob = next((s for s in mask_rl.outputs if s.name == "IndexOB"), None)

        if index_ob and not index_ob.links:
            tree.links.new(index_ob, compare.inputs[0])
