"""Addon preferences for persistent user defaults."""

import bpy
from bpy.types import AddonPreferences
from bpy.props import BoolProperty, EnumProperty, StringProperty


class DEPTHMAP_AddonPreferences(AddonPreferences):
    """Persistent addon preferences accessible via Edit > Preferences > Add-ons."""

    bl_idname = "depth_map_generator"

    default_depth_output_dir: StringProperty(
        name="Default Depth Output",
        description="Default directory for depth map output",
        default="//depth_maps/",
        subtype='DIR_PATH',
    )

    default_mask_output_dir: StringProperty(
        name="Default Mask Output",
        description="Default directory for mask map output",
        default="//mask_maps/",
        subtype='DIR_PATH',
    )

    default_bit_depth: EnumProperty(
        name="Default Bit Depth",
        description="Default bit depth for new scenes",
        items=[
            ('8', "8-bit", "Standard 8-bit PNG"),
            ('16', "16-bit", "High precision 16-bit PNG (recommended)"),
        ],
        default='16',
    )

    comfyui_input_dir: StringProperty(
        name="ComfyUI Input Directory",
        description="Optional path to ComfyUI/input/ for direct export",
        default="",
        subtype='DIR_PATH',
    )

    auto_create_directories: BoolProperty(
        name="Auto-Create Directories",
        description="Automatically create output directories if they don't exist",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "default_depth_output_dir")
        layout.prop(self, "default_mask_output_dir")
        layout.prop(self, "default_bit_depth")
        layout.separator()
        layout.prop(self, "comfyui_input_dir")
        layout.prop(self, "auto_create_directories")
