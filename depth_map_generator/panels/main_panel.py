"""Main parent panel in the 3D Viewport sidebar."""

import bpy
from bpy.types import Panel


class DEPTHMAP_PT_main_panel(Panel):
    """Parent panel for depth map controls in the 3D View sidebar"""

    bl_label = "Depth Map Generator"
    bl_idname = "DEPTHMAP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Depth Map"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if not hasattr(scene, 'depth_map_settings'):
            layout.label(text="Error: Addon not properly initialized", icon='ERROR')
            return

        settings = scene.depth_map_settings

        # Setup / Reset buttons
        layout.operator("depthmap.setup", text="Setup Depth Map",
                         icon='OUTLINER_DATA_CAMERA')
        layout.operator("depthmap.reset", text="Reset Compositing", icon='X')

        # Setup status indicator
        if settings.setup_complete:
            layout.label(text="Setup Complete", icon='CHECKMARK')
