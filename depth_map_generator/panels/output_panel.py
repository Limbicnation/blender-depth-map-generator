"""Output sub-panel - output method, file paths, animation, render buttons."""

from bpy.types import Panel


class DEPTHMAP_PT_output(Panel):
    """Sub-panel for output configuration and rendering"""

    bl_label = "Output"
    bl_idname = "DEPTHMAP_PT_output"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Depth Map"
    bl_parent_id = "DEPTHMAP_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.depth_map_settings

        # Output method selector
        layout.prop(settings, "depth_output_method")

        if settings.depth_output_method == 'FILE_OUTPUT':
            layout.prop(settings, "output_path", text="")

            # Animation options
            layout.prop(settings, "render_animation")
            if settings.render_animation:
                box = layout.box()
                box.prop(settings, "use_scene_frame_range")
                if not settings.use_scene_frame_range:
                    row = box.row(align=True)
                    row.prop(settings, "frame_start")
                    row.prop(settings, "frame_end")
                else:
                    row = box.row()
                    row.label(
                        text=f"Scene Range: {context.scene.frame_start}"
                             f" - {context.scene.frame_end}"
                    )

        # Render buttons
        layout.separator()
        if (settings.depth_output_method == 'FILE_OUTPUT'
                and settings.render_animation):
            layout.operator("depthmap.render", text="Render Depth Animation",
                             icon='RENDER_ANIMATION')
        else:
            layout.operator("depthmap.render", text="Render Depth Map",
                             icon='RENDER_STILL')
