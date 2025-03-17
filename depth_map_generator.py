bl_info = {
    "name": "Depth Map Generator",
    "author": "Your Name",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Depth Map",
    "description": "Automates depth map setup and rendering",
    "category": "Render",
}

import bpy
import os
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatProperty, BoolProperty, EnumProperty, PointerProperty, BoolProperty


class DEPTHMAP_PT_main_panel(Panel):
    """Creates a Panel in the 3D View sidebar for depth map controls"""
    bl_label = "Depth Map Generator"
    bl_idname = "DEPTHMAP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Depth Map"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        depth_settings = scene.depth_map_settings

        # Main setup button
        layout.operator("depthmap.setup", text="Setup Depth Map", icon='OUTLINER_DATA_CAMERA')
        
        # Settings section
        box = layout.box()
        box.label(text="Depth Settings:")
        
        # Depth range settings
        box.prop(depth_settings, "use_custom_range")
        if depth_settings.use_custom_range:
            row = box.row()
            row.prop(depth_settings, "near_distance")
            row.prop(depth_settings, "far_distance")
        
        # Output options
        box = layout.box()
        box.label(text="Output Options:")
        box.prop(depth_settings, "depth_output_method")
        
        if depth_settings.depth_output_method == 'FILE_OUTPUT':
            box.prop(depth_settings, "output_path", text="")
        
        # Render buttons
        layout.operator("depthmap.render", text="Render Depth Map", icon='RENDER_STILL')
        layout.operator("depthmap.reset", text="Reset Compositing", icon='X')

        # Setup status indicator
        if hasattr(scene, "depth_map_setup_complete") and scene.depth_map_setup_complete:
            layout.label(text="✓ Setup Complete", icon='CHECKMARK')


class DEPTHMAP_OT_setup(Operator):
    """Sets up the scene for depth map rendering"""
    bl_idname = "depthmap.setup"
    bl_label = "Setup Depth Map"
    bl_description = "Configure render passes and compositing nodes for depth map"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        depth_settings = scene.depth_map_settings
        
        try:
            # 1. Enable Z pass
            view_layer = context.view_layer
            view_layer.use_pass_z = True
            
            # 2. Set up compositing
            scene.use_nodes = True
            tree = scene.node_tree
            
            # Clear existing nodes if this is not a refresh of an existing setup
            if not hasattr(scene, "depth_map_setup_complete") or not scene.depth_map_setup_complete:
                for node in tree.nodes:
                    tree.nodes.remove(node)
                
                # Create nodes - now with descriptive names
                render_layers = tree.nodes.new(type='CompositorNodeRLayers')
                render_layers.name = "DM_RenderLayers"
                render_layers.label = "Depth Map Input"
                render_layers.location = (0, 0)
                
                # Normalize node
                normalize = tree.nodes.new(type='CompositorNodeNormalize')
                normalize.name = "DM_Normalize"
                normalize.label = "Normalize Depth"
                normalize.location = (300, 0)
                
                # Conditionally add map range node
                if depth_settings.use_custom_range:
                    map_range = tree.nodes.new(type='CompositorNodeMapRange')
                    map_range.name = "DM_RangeMapper"
                    map_range.label = "Depth Range Adjuster"
                    map_range.location = (200, 0)
                    map_range.inputs['From Min'].default_value = 0
                    map_range.inputs['From Max'].default_value = 100
                    # Invert the output range - this is the key fix for black depth maps
                    map_range.inputs['To Min'].default_value = 1.0  # Was 0.0
                    map_range.inputs['To Max'].default_value = 0.0  # Was 1.0
                    
                    # Update values based on settings
                    map_range.inputs['From Min'].default_value = depth_settings.near_distance
                    map_range.inputs['From Max'].default_value = depth_settings.far_distance
                    
                    # Link render layers Z to map range
                    tree.links.new(render_layers.outputs['Depth'], map_range.inputs['Value'])
                    # Link map range to normalize
                    tree.links.new(map_range.outputs['Value'], normalize.inputs[0])
                else:
                    # Link directly to normalize if not using custom range
                    tree.links.new(render_layers.outputs['Depth'], normalize.inputs[0])
                    
                    # Add an invert node for better depth visualization
                    invert = tree.nodes.new(type='CompositorNodeMath')
                    invert.name = "DM_Inverter"
                    invert.label = "Invert Depth"
                    invert.operation = 'SUBTRACT'
                    invert.inputs[0].default_value = 1.0
                    invert.location = (400, 0)
                    tree.links.new(normalize.outputs[0], invert.inputs[1])
                    normalize = invert  # Redirect the following connections to use the invert node
                
                # ALWAYS create a Composite node - this fixes the Viewer node error
                composite = tree.nodes.new(type='CompositorNodeComposite')
                composite.name = "DM_Composite"
                composite.label = "Depth Map Output"
                composite.location = (800, -100)  # Position below other output nodes
                tree.links.new(output_source.outputs[0], composite.inputs['Image'])
                
                # Set up output based on selected method
                if depth_settings.depth_output_method == 'COMPOSITE':
                    # Just reposition the composite node we already created
                    composite.location = (800, 0)
                    
                elif depth_settings.depth_output_method == 'VIEWER':
                    # Create viewer node in addition to the composite node
                    viewer = tree.nodes.new(type='CompositorNodeViewer')
                    viewer.name = "DM_Viewer"
                    viewer.label = "Depth Preview"
                    viewer.location = (800, 50)
                    tree.links.new(output_source.outputs[0], viewer.inputs['Image'])
                    
                elif depth_settings.depth_output_method == 'FILE_OUTPUT':
                    # Check and create output directory
                    output_dir = bpy.path.abspath(depth_settings.output_path)
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # File output node in addition to the composite node
                    file_output = tree.nodes.new(type='CompositorNodeOutputFile')
                    file_output.name = "DM_FileOutput"
                    file_output.label = "Depth Map Files"
                    file_output.location = (800, 100)
                    file_output.base_path = depth_settings.output_path
                    # Set filename to include "depth"
                    file_output.file_slots[0].path = "depth_"
                    tree.links.new(output_source.outputs[0], file_output.inputs['Image'])
            else:
                # Just update existing nodes
                self._update_node_settings(context, tree, depth_settings)
                
            # Mark setup as complete
            scene.depth_map_setup_complete = True
            
            self.report({'INFO'}, "Depth map setup complete")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Setup failed: {str(e)}")
            return {'CANCELLED'}

    def _update_node_settings(self, context, tree, depth_settings):
        """Updates existing node settings without recreating them"""
        # Find existing nodes by name
        range_node = tree.nodes.get("DM_RangeMapper")
        if range_node:
            if depth_settings.use_custom_range:
                range_node.inputs['From Min'].default_value = depth_settings.near_distance
                range_node.inputs['From Max'].default_value = depth_settings.far_distance
            else:
                # Reset to default auto-range values
                range_node.inputs['From Min'].default_value = 0.1
                range_node.inputs['From Max'].default_value = 1000.0
            
            # Ensure proper inversion
            range_node.inputs['To Min'].default_value = 1.0
            range_node.inputs['To Max'].default_value = 0.0
        
        # Update contrast settings
        contrast_node = tree.nodes.get("DM_Contrast")
        if contrast_node:
            # Ensure contrast is set properly
            contrast_node.inputs['Contrast'].default_value = 0.2
        
        # Update color ramp settings - just ensure it exists
        ramp_node = tree.nodes.get("DM_ColorRamp")
        if not ramp_node:
            # If somehow the color ramp is missing, rebuild the node setup
            self.report({'WARNING'}, "Node setup incomplete - rebuilding")
            context.scene.depth_map_setup_complete = False
            return
        
        # Update file output path if needed
        file_output = tree.nodes.get("DM_FileOutput")
        if file_output and depth_settings.depth_output_method == 'FILE_OUTPUT':
            # Check and create output directory
            output_dir = bpy.path.abspath(depth_settings.output_path)
            os.makedirs(output_dir, exist_ok=True)
            file_output.base_path = depth_settings.output_path


class DEPTHMAP_OT_render(Operator):
    """Renders the depth map"""
    bl_idname = "depthmap.render"
    bl_label = "Render Depth Map"
    bl_description = "Render the depth map with current settings"
    
    def execute(self, context):
        try:
            # Only run setup if not already set up or if settings have changed
            if not hasattr(context.scene, "depth_map_setup_complete") or not context.scene.depth_map_setup_complete:
                bpy.ops.depthmap.setup()
            
            # Then render
            bpy.ops.render.render('INVOKE_DEFAULT')
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Render failed: {str(e)}")
            return {'CANCELLED'}


class DEPTHMAP_OT_reset(Operator):
    """Resets the compositing setup"""
    bl_idname = "depthmap.reset"
    bl_label = "Reset Compositing"
    bl_description = "Remove depth map nodes and restore default setup"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            scene = context.scene
            
            # Disable Z pass
            context.view_layer.use_pass_z = False
            
            # Clear node tree
            if scene.use_nodes:
                tree = scene.node_tree
                for node in tree.nodes:
                    tree.nodes.remove(node)
                
                # Add back basic nodes
                render_layers = tree.nodes.new(type='CompositorNodeRLayers')
                render_layers.location = (0, 0)
                
                composite = tree.nodes.new(type='CompositorNodeComposite')
                composite.location = (300, 0)
                
                tree.links.new(render_layers.outputs['Image'], composite.inputs['Image'])
            
            # Reset setup flag
            scene.depth_map_setup_complete = False
            
            self.report({'INFO'}, "Compositing reset to default")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Reset failed: {str(e)}")
            return {'CANCELLED'}


class DepthMapSettings(PropertyGroup):
    """Property group to store depth map settings"""
    use_custom_range: BoolProperty(
        name="Custom Range",
        description="Specify custom near and far distances for depth range",
        default=False
    )
    
    near_distance: FloatProperty(
        name="Near",
        description="Near distance for depth range (smaller values = closer objects)",
        min=0.01,
        max=1000.0,
        default=0.1
    )
    
    far_distance: FloatProperty(
        name="Far",
        description="Far distance for depth range (larger values = distant objects)",
        min=0.1,
        max=10000.0,
        default=100.0
    )
    
    depth_output_method: EnumProperty(
        name="Output Method",
        description="How to output the depth map",
        items=[
            ('COMPOSITE', "Composite", "Send depth map to compositor output"),
            ('VIEWER', "Viewer", "Send depth map to viewer node for preview"),
            ('FILE_OUTPUT', "File Output", "Save depth map to a separate file")
        ],
        default='VIEWER'  # Changed default to Viewer for better usability
    )
    
    output_path: bpy.props.StringProperty(
        name="Output Path",
        description="Path to save depth map files",
        default="//depth_maps/",
        subtype='DIR_PATH'
    )


# Registration
classes = (
    DepthMapSettings,
    DEPTHMAP_PT_main_panel,
    DEPTHMAP_OT_setup,
    DEPTHMAP_OT_render,
    DEPTHMAP_OT_reset
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.depth_map_settings = PointerProperty(type=DepthMapSettings)
    # Register setup tracking property
    bpy.types.Scene.depth_map_setup_complete = BoolProperty(default=False)

def unregister():
    # Clean up tracking property
    if hasattr(bpy.types.Scene, "depth_map_setup_complete"):
        del bpy.types.Scene.depth_map_setup_complete
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.depth_map_settings

if __name__ == "__main__":
    register()