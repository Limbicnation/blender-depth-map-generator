"""Setup operator - configures render passes and compositing nodes."""

import bpy
from bpy.types import Operator

from ..utils import nodes


class DEPTHMAP_OT_setup(Operator):
    """Sets up the scene for depth map rendering"""

    bl_idname = "depthmap.setup"
    bl_label = "Setup Depth Map"
    bl_description = "Configure render passes and compositing nodes for depth map"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        settings = scene.depth_map_settings

        try:
            # Get addon preferences
            prefs = context.preferences.addons.get("depth_map_generator")
            prefs = prefs.preferences if prefs else None

            # Enable Z pass
            view_layer = context.view_layer
            view_layer.use_pass_z = True

            # Enable Object Index pass if mask is enabled with Object Index source
            if settings.mask_enabled and settings.mask_source == 'OBJECT_INDEX':
                view_layer.use_pass_object_index = True

            # Set up compositing
            scene.use_nodes = True
            tree = scene.node_tree

            if not settings.setup_complete:
                # Fresh setup: clear and rebuild
                for node in tree.nodes:
                    tree.nodes.remove(node)

                # Build depth pipeline
                render_layers, output_socket = nodes.create_depth_pipeline(
                    tree, settings, prefs
                )

                # Create output nodes
                nodes.create_output_nodes(tree, settings, output_socket, prefs)

                # Build mask pipeline if enabled
                if settings.mask_enabled:
                    nodes.create_mask_pipeline(tree, render_layers, settings, prefs)

            else:
                # Update existing nodes
                if not nodes.update_depth_nodes(tree, settings):
                    self.report({'WARNING'}, "Node setup incomplete - rebuilding")
                    settings.setup_complete = False
                    return self.execute(context)

            settings.setup_complete = True
            self.report({'INFO'}, "Depth map setup complete")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Setup failed: {str(e)}")
            return {'CANCELLED'}
