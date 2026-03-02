"""Render operator - handles both single frame and animation sequence rendering."""

import bpy
from bpy.types import Operator

from ..utils import paths


class DEPTHMAP_OT_render(Operator):
    """Renders the depth map or animation sequence"""

    bl_idname = "depthmap.render"
    bl_label = "Render Depth Map"
    bl_description = "Render the depth map with current settings"

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
