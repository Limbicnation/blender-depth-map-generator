"""Mask sub-panel - alpha mask export settings and controls."""

from bpy.types import Panel


class DEPTHMAP_PT_mask(Panel):
    """Sub-panel for alpha mask export configuration"""

    bl_label = "Alpha Mask"
    bl_idname = "DEPTHMAP_PT_mask"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Depth Map"
    bl_parent_id = "DEPTHMAP_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        settings = context.scene.depth_map_settings
        self.layout.prop(settings, "mask_enabled", text="")

    def draw(self, context):
        layout = self.layout
        settings = context.scene.depth_map_settings
        layout.active = settings.mask_enabled

        # Mask source selector
        layout.prop(settings, "mask_source")

        # Cryptomatte warning for non-Cycles
        if (settings.mask_source == 'CRYPTOMATTE'
                and context.scene.render.engine != 'CYCLES'):
            layout.label(text="Cryptomatte requires Cycles!", icon='ERROR')

        # Object Index settings
        if settings.mask_source == 'OBJECT_INDEX':
            layout.prop(settings, "mask_index")
            layout.label(
                text="Set Pass Index on object: Properties > Object > Relations",
                icon='INFO',
            )

        # Format and output path
        layout.prop(settings, "mask_output_format")
        layout.prop(settings, "mask_output_path", text="")

        # Export button
        layout.separator()
        row = layout.row()
        row.enabled = settings.mask_enabled
        if (settings.depth_output_method == 'FILE_OUTPUT'
                and settings.render_animation):
            row.operator("depthmap.export_mask", text="Export Mask Animation",
                          icon='RENDER_ANIMATION')
        else:
            row.operator("depthmap.export_mask", text="Export Mask",
                          icon='RENDER_STILL')
