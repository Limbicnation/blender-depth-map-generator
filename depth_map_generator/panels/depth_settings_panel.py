"""Depth settings sub-panel - normalization, range, contrast controls."""

from bpy.types import Panel


class DEPTHMAP_PT_depth_settings(Panel):
    """Sub-panel for depth pass configuration"""

    bl_label = "Depth Settings"
    bl_idname = "DEPTHMAP_PT_depth_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Depth Map"
    bl_parent_id = "DEPTHMAP_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.depth_map_settings

        # Normalization mode
        layout.prop(settings, "depth_normalization")

        # Custom depth range
        layout.prop(settings, "use_custom_range")
        if settings.use_custom_range:
            row = layout.row(align=True)
            row.prop(settings, "near_distance")
            row.prop(settings, "far_distance")

        # Scale factor (relevant for LOGARITHMIC and RAW)
        if settings.depth_normalization in {'LOGARITHMIC', 'RAW'}:
            layout.prop(settings, "depth_scale_factor")

        # Bit depth
        layout.prop(settings, "output_bit_depth")

        # Contrast / Brightness
        layout.prop(settings, "contrast_value")
        layout.prop(settings, "brightness_value")

        # Preview toggle
        layout.prop(settings, "preview_before_export")
