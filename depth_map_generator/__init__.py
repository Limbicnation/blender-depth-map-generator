"""Depth Map Generator v2.0 - Blender addon for depth map and alpha mask rendering."""

bl_info = {
    "name": "Depth Map Generator",
    "author": "Gero Doll",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Depth Map",
    "description": "Depth map and alpha mask generation for ComfyUI workflows",
    "category": "Render",
}

import bpy
from bpy.props import PointerProperty

from .properties import DepthMapSettings
from .preferences import DEPTHMAP_AddonPreferences
from .operators.setup import DEPTHMAP_OT_setup
from .operators.render import DEPTHMAP_OT_render
from .operators.reset import DEPTHMAP_OT_reset
from .operators.mask_export import DEPTHMAP_OT_export_mask
from .panels.main_panel import DEPTHMAP_PT_main_panel
from .panels.depth_settings_panel import DEPTHMAP_PT_depth_settings
from .panels.output_panel import DEPTHMAP_PT_output
from .panels.mask_panel import DEPTHMAP_PT_mask

# Registration order: PropertyGroup -> Preferences -> Operators -> Parent Panel -> Sub-panels
classes = (
    DepthMapSettings,
    DEPTHMAP_AddonPreferences,
    DEPTHMAP_OT_setup,
    DEPTHMAP_OT_render,
    DEPTHMAP_OT_reset,
    DEPTHMAP_OT_export_mask,
    DEPTHMAP_PT_main_panel,
    DEPTHMAP_PT_depth_settings,
    DEPTHMAP_PT_output,
    DEPTHMAP_PT_mask,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.depth_map_settings = PointerProperty(type=DepthMapSettings)

    # Migration: remove legacy loose property from old versions
    if hasattr(bpy.types.Scene, "depth_map_setup_complete"):
        del bpy.types.Scene.depth_map_setup_complete


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.Scene, "depth_map_settings"):
        del bpy.types.Scene.depth_map_settings


if __name__ == "__main__":
    register()
