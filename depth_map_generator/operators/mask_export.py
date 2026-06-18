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
    bl_options = {'REGISTER', 'UNDO'}

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
            if settings.mask_source == 'CRYPTOMATTE' and scene.render.engine != 'CYCLES':
                self.report(
                    {'ERROR'},
                    "Cryptomatte requires Cycles render engine. "
                    "Switch to Cycles or use Object Index mode.",
                )
                return {'CANCELLED'}

            # Explicitly enable the Object Index pass *before* we look for or
            # build the mask pipeline. create_mask_pipeline() also does this,
            # but enabling here guarantees the pass is on even when the pipeline
            # node already exists from a setup that ran with mask disabled.
            if settings.mask_source == 'OBJECT_INDEX':
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
                    {'ERROR'},
                    "Mask pipeline is not connected. "
                    "Try 'Reset Compositing' then 'Setup Depth Map' with mask enabled.",
                )
                return {'CANCELLED'}

            # Validate output path before committing to a render.
            output_dir = paths.get_mask_output_dir(settings, prefs)
            is_valid, error_msg = paths.validate_output_path(output_dir)
            if not is_valid:
                self.report({'ERROR'}, f"Invalid mask output path: {error_msg}")
                return {'CANCELLED'}

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
                    {'INFO'},
                    f"Exporting mask animation: {frame_count} frames to {output_dir}",
                )
                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
            else:
                self.report({'INFO'}, "Exporting single mask frame")
                bpy.ops.render.render('EXEC_DEFAULT')
                self._verify_mask_output(output_dir)

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Mask export failed: {str(e)}")
            return {'CANCELLED'}

    def _verify_mask_output(self, output_dir):
        """Warn (not fail) if no mask PNG was written after a blocking render.

        output_dir is already absolute (paths.get_mask_output_dir resolves it),
        but we re-resolve defensively in case a caller passes a Blender-style
        relative path.
        """
        abs_dir = bpy.path.abspath(output_dir)
        if not os.path.isdir(abs_dir):
            return
        png_files = [
            f for f in os.listdir(abs_dir)
            if f.lower().endswith('.png') and 'mask' in f.lower()
        ]
        if not png_files:
            self.report(
                {'WARNING'},
                f"Render completed but no mask files found in {abs_dir}. "
                "Check compositor node connections.",
            )
