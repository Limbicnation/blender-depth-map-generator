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

            # Enable render passes on view layer
            view_layer = context.view_layer
            view_layer.use_pass_z = True

            if settings.mask_enabled and settings.mask_source == 'OBJECT_INDEX':
                view_layer.use_pass_object_index = True

            # Force Blender to process pass changes before we create
            # compositor nodes that depend on those passes (IndexOB, etc.)
            scene.update_tag()
            context.evaluated_depsgraph_get().update()

            # Set up compositing
            scene.use_nodes = True
            tree = scene.node_tree

            if not settings.setup_complete:
                # Fresh setup: remove only DM_ nodes to preserve user's setup
                nodes.remove_dm_nodes(tree)

                # Build depth pipeline
                render_layers, output_socket = nodes.create_depth_pipeline(
                    tree, settings, prefs
                )

                # Create output nodes
                nodes.create_output_nodes(tree, settings, output_socket, prefs)

                # Build mask pipeline if enabled (uses separate RenderLayers)
                if settings.mask_enabled:
                    try:
                        nodes.create_mask_pipeline(
                            tree, settings, prefs
                        )
                    except Exception as e:
                        self.report(
                            {'WARNING'},
                            f"Depth setup OK, but mask failed: {str(e)}"
                        )

            else:
                # Update existing nodes (may also create mask pipeline
                # if mask was enabled after initial setup)
                try:
                    if not nodes.update_depth_nodes(tree, settings, prefs):
                        self.report({'WARNING'}, "Node setup incomplete - rebuilding")
                        settings.setup_complete = False
                        return self.execute(context)
                except Exception as e:
                    self.report(
                        {'WARNING'},
                        f"Depth update OK, but mask failed: {str(e)}"
                    )

            settings.setup_complete = True
            self.report({'INFO'}, "Depth map setup complete")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Setup failed: {str(e)}")
            return {'CANCELLED'}
