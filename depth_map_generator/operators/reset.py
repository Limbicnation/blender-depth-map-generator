"""Reset operator - cleans up compositing nodes and restores defaults."""

import bpy
from bpy.types import Operator

from ..utils import nodes


class DEPTHMAP_OT_reset(Operator):
    """Resets the compositing setup"""

    bl_idname = "depthmap.reset"
    bl_label = "Reset Compositing"
    bl_description = "Remove depth map nodes and restore default setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            scene = context.scene

            # Disable render passes
            context.view_layer.use_pass_z = False
            context.view_layer.use_pass_object_index = False

            if scene.use_nodes:
                tree = scene.node_tree
                # Remove only DM_ nodes to preserve user's existing setup
                nodes.remove_dm_nodes(tree)

                # If compositor is now empty, restore default RenderLayers -> Composite
                if len(tree.nodes) == 0:
                    nodes.clear_all_nodes(tree)

            # Reset setup flag
            scene.depth_map_settings.setup_complete = False

            self.report({'INFO'}, "Compositing reset to default")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Reset failed: {str(e)}")
            return {'CANCELLED'}
