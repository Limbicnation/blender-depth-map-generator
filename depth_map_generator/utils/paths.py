"""Path resolution and directory management for depth map output."""

import os

import bpy


def resolve_output_path(path, create=True, prefs=None):
    """Resolve a Blender path (possibly relative with //) to absolute and optionally create it.

    Args:
        path: Blender-style path string
        create: If True, create the directory if it doesn't exist
        prefs: AddonPreferences (optional) - respects auto_create_directories

    Returns:
        Absolute path string
    """
    abs_path = bpy.path.abspath(path)
    should_create = create
    if prefs and hasattr(prefs, 'auto_create_directories'):
        should_create = create and prefs.auto_create_directories
    if should_create:
        os.makedirs(abs_path, exist_ok=True)
    return abs_path


def get_depth_output_dir(settings, prefs=None):
    """Get the resolved depth map output directory.

    Uses scene-level output_path if set, otherwise falls back to addon preferences.

    Args:
        settings: DepthMapSettings property group
        prefs: AddonPreferences (optional)

    Returns:
        Absolute path string
    """
    path = settings.output_path
    if not path and prefs:
        path = prefs.default_depth_output_dir
    if not path:
        path = "//depth_maps/"
    return bpy.path.abspath(path)


def get_mask_output_dir(settings, prefs=None):
    """Get the resolved mask map output directory.

    Uses scene-level mask_output_path if set, otherwise falls back to addon preferences.

    Args:
        settings: DepthMapSettings property group
        prefs: AddonPreferences (optional)

    Returns:
        Absolute path string
    """
    path = settings.mask_output_path
    if not path and prefs:
        path = prefs.default_mask_output_dir
    if not path:
        path = "//mask_maps/"
    return bpy.path.abspath(path)


def validate_output_path(path):
    """Check if a path is writable.

    Args:
        path: Absolute directory path

    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    abs_path = bpy.path.abspath(path)
    parent = os.path.dirname(abs_path.rstrip(os.sep))

    if not os.path.exists(parent):
        return False, f"Parent directory does not exist: {parent}"

    if os.path.exists(abs_path) and not os.access(abs_path, os.W_OK):
        return False, f"Directory is not writable: {abs_path}"

    return True, None
