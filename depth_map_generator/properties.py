"""DepthMapSettings PropertyGroup - all addon settings stored per scene."""

import bpy
from bpy.types import PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)


class DepthMapSettings(PropertyGroup):
    """Property group storing all depth map addon settings."""

    # --- Setup tracking (replaces loose scene.depth_map_setup_complete) ---
    setup_complete: BoolProperty(
        name="Setup Complete",
        description="Whether the depth map compositing pipeline has been configured",
        default=False,
    )

    # --- Existing depth range properties (preserved for .blend compatibility) ---
    use_custom_range: BoolProperty(
        name="Custom Range",
        description="Specify custom near and far distances for depth range",
        default=False,
    )

    near_distance: FloatProperty(
        name="Near",
        description="Near distance for depth range (smaller values = closer objects)",
        min=0.01,
        max=1000.0,
        default=0.1,
    )

    far_distance: FloatProperty(
        name="Far",
        description="Far distance for depth range (larger values = distant objects)",
        min=0.1,
        max=10000.0,
        default=100.0,
    )

    # --- Existing output properties (preserved) ---
    depth_output_method: EnumProperty(
        name="Output Method",
        description="How to output the depth map",
        items=[
            ('COMPOSITE', "Composite", "Send depth map to compositor output"),
            ('VIEWER', "Viewer", "Send depth map to viewer node for preview"),
            ('FILE_OUTPUT', "File Output", "Save depth map to a separate file"),
        ],
        default='VIEWER',
    )

    output_path: StringProperty(
        name="Output Path",
        description="Path to save depth map files",
        default="//depth_maps/",
        subtype='DIR_PATH',
    )

    # --- Existing animation properties (preserved) ---
    render_animation: BoolProperty(
        name="Render Animation",
        description="Render depth maps for the entire animation sequence",
        default=False,
    )

    use_scene_frame_range: BoolProperty(
        name="Use Scene Frame Range",
        description="Use the scene's start and end frame settings",
        default=True,
    )

    frame_start: IntProperty(
        name="Start Frame",
        description="First frame to render in the animation sequence",
        default=1,
        min=0,
    )

    frame_end: IntProperty(
        name="End Frame",
        description="Last frame to render in the animation sequence",
        default=250,
        min=0,
    )

    # --- New v2.0: Depth pass controls ---
    depth_normalization: EnumProperty(
        name="Normalization",
        description="How to normalize raw depth values",
        items=[
            ('LINEAR', "Linear",
             "Linear mapping with inversion (default, good for most scenes)"),
            ('LOGARITHMIC', "Logarithmic",
             "Logarithmic mapping for more near-field detail"),
            ('RAW', "Raw",
             "Unprocessed depth values (no MapRange or ColorRamp)"),
        ],
        default='LINEAR',
    )

    depth_scale_factor: FloatProperty(
        name="Scale Factor",
        description="Multiplier applied to raw depth values before normalization",
        min=0.001,
        max=1000.0,
        default=1.0,
    )

    output_bit_depth: EnumProperty(
        name="Bit Depth",
        description="Output bit depth for PNG files (16-bit recommended for ComfyUI)",
        items=[
            ('8', "8-bit", "Standard 8-bit PNG"),
            ('16', "16-bit", "High precision 16-bit PNG (recommended)"),
        ],
        default='16',
    )

    contrast_value: FloatProperty(
        name="Contrast",
        description="Contrast adjustment for depth visualization",
        min=-1.0,
        max=1.0,
        default=0.2,
    )

    brightness_value: FloatProperty(
        name="Brightness",
        description="Brightness adjustment for depth visualization",
        min=-1.0,
        max=1.0,
        default=0.0,
    )

    preview_before_export: BoolProperty(
        name="Preview",
        description="Add a Viewer node alongside File Output for preview",
        default=False,
    )

    # --- New v2.0: Alpha mask export ---
    mask_enabled: BoolProperty(
        name="Enable Mask Export",
        description="Enable alpha mask export alongside depth maps",
        default=False,
    )

    mask_source: EnumProperty(
        name="Mask Source",
        description="Method for generating the alpha mask",
        items=[
            ('OBJECT_INDEX', "Object Index",
             "Use Object Pass Index to isolate objects"),
            ('CRYPTOMATTE', "Cryptomatte",
             "Use Cryptomatte for precise anti-aliased masks (Cycles only)"),
        ],
        default='OBJECT_INDEX',
    )

    mask_output_format: EnumProperty(
        name="Mask Format",
        description="Output format for the mask",
        items=[
            ('GRAYSCALE', "Grayscale PNG",
             "Single channel mask (loads directly as mask in ComfyUI)"),
            ('RGBA_PNG', "RGBA PNG",
             "RGBA with alpha channel (use SplitImageWithAlpha in ComfyUI)"),
        ],
        default='GRAYSCALE',
    )

    mask_index: IntProperty(
        name="Pass Index",
        description="Object Pass Index to isolate (set on object Properties > Object > Relations)",
        min=0,
        max=32767,
        default=1,
    )

    mask_output_path: StringProperty(
        name="Mask Output Path",
        description="Path to save mask map files",
        default="//mask_maps/",
        subtype='DIR_PATH',
    )
