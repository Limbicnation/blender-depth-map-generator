"""Render operator - handles both single frame and animation sequence rendering."""

import bpy
from bpy.types import Operator

from ..utils import nodes, paths


class DEPTHMAP_OT_render(Operator):
    """Renders the depth map or animation sequence."""

    bl_idname = "depthmap.render"
    bl_label = "Render Depth Map"
    bl_description = "Render the depth map with current settings"

    def execute(self, context):
        try:
            scene = context.scene
            settings = scene.depth_map_settings
            tree = scene.node_tree
            prefs_addon = context.preferences.addons.get("depth_map_generator")
            prefs = prefs_addon.preferences if prefs_addon else None

            # Auto-setup if not already configured.
            if not settings.setup_complete:
                bpy.ops.depthmap.setup()

            # Resolve and validate output path when using file output.
            output_dir = ""
            if settings.depth_output_method == "FILE_OUTPUT":
                output_dir = paths.get_depth_output_dir(settings, prefs)
                is_valid, error_msg = paths.validate_output_path(output_dir)
                if not is_valid:
                    self.report(
                        {"ERROR"},
                        f"Invalid depth output path: {error_msg}",
                    )
                    return {"CANCELLED"}

            if settings.depth_output_method == "FILE_OUTPUT" and settings.render_animation:
                # Set custom frame range if not using scene range.
                if not settings.use_scene_frame_range:
                    scene.frame_start = settings.frame_start
                    scene.frame_end = settings.frame_end

                frame_count = scene.frame_end - scene.frame_start + 1
                self.report(
                    {"INFO"},
                    f"Rendering depth animation: {frame_count} frames to {output_dir}",
                )
                bpy.ops.render.render("INVOKE_DEFAULT", animation=True)
            else:
                self.report({"INFO"}, "Rendering single depth map frame")
                # EXEC_DEFAULT blocks until the compositor finishes evaluating,
                # so the Viewer node is populated and the Image Editor can show
                # the depth preview without manual node selection. Animations
                # stay on INVOKE_DEFAULT to avoid freezing the UI.
                bpy.ops.render.render("EXEC_DEFAULT")
                self._activate_viewer(tree)

            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Render failed: {str(e)}")
            return {"CANCELLED"}

    @staticmethod
    def _activate_viewer(tree):
        """Set DM_Viewer as the active compositor node and refresh the UI.

        After a blocking (EXEC_DEFAULT) render the compositor has already
        evaluated, so the Viewer node holds the depth image. Marking it as the
        active/selected node and tagging Image Editor areas for redraw makes
        Blender display the depth preview without the user having to click the
        node manually.
        """
        viewer = nodes.find_dm_node(tree, "DM_Viewer")
        if not viewer:
            return

        # Selecting + setting active tells the Image Editor (in Viewer Node
        # mode) which node to display.
        viewer.select = True
        tree.nodes.active = viewer

        # Force every Image Editor area to redraw so the preview appears.
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "IMAGE_EDITOR":
                    area.tag_redraw()
