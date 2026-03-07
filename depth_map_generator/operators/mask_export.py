"""Mask export operator - renders alpha mask for ComfyUI workflows."""

import bpy
from bpy.types import Operator

from ..utils import nodes, paths


class DEPTHMAP_OT_export_mask(Operator):
    """Exports an alpha mask using Object Index or Cryptomatte"""

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

            # Ensure mask pipeline exists, rebuild if missing
            mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")
            if not mask_node:
                nodes.create_mask_pipeline(tree, settings, prefs)
                mask_node = nodes.find_dm_node(tree, "DM_MaskFileOutput")

            # Validate the mask FileOutput is actually connected
            if not mask_node or not mask_node.inputs[0].links:
                self.report(
                    {'ERROR'},
                    "Mask pipeline is not connected. "
                    "Try 'Reset Compositing' then 'Setup Depth Map' with mask enabled."
                )
                return {'CANCELLED'}

            # Validate output path before committing to a render
            output_dir = paths.get_mask_output_dir(settings, prefs)
            is_valid, error_msg = paths.validate_output_path(output_dir)
            if not is_valid:
                self.report({'ERROR'}, f"Invalid mask output path: {error_msg}")
                return {'CANCELLED'}

            # Render — mask animation is independent of depth output method
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
