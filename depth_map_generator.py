bl_info = {
    "name": "Depth Map Generator",
    "author": "Your Name",
    "version": (1, 2),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Depth Map",
    "description": "Automates depth map setup and rendering for stills and animations",
    "category": "Render",
}

import bpy
import os
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import FloatProperty, BoolProperty, EnumProperty, PointerProperty


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
            
            # Animation options (only available with file output)
            box.prop(depth_settings, "render_animation")
            
            if depth_settings.render_animation:
                sub_box = box.box()
                sub_box.prop(depth_settings, "use_scene_frame_range")
                
                if not depth_settings.use_scene_frame_range:
                    row = sub_box.row(align=True)
                    row.prop(depth_settings, "frame_start")
                    row.prop(depth_settings, "frame_end")
                else:
                    # Display scene frame range as info
                    row = sub_box.row()
                    row.label(text=f"Scene Range: {context.scene.frame_start} - {context.scene.frame_end}")
        
        # Render buttons
        if depth_settings.depth_output_method == 'FILE_OUTPUT' and depth_settings.render_animation:
            layout.operator("depthmap.render", text="Render Depth Animation", icon='RENDER_ANIMATION')
        else:
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
                
                # IMPROVED DEPTH MAP PIPELINE:
                
                # 1. Map Range node - always use this for better control
                map_range = tree.nodes.new(type='CompositorNodeMapRange')
                map_range.name = "DM_RangeMapper"
                map_range.label = "Depth Range Adjuster"
                map_range.location = (200, 0)
                
                # Default values ensure full range
                if depth_settings.use_custom_range:
                    map_range.inputs['From Min'].default_value = depth_settings.near_distance
                    map_range.inputs['From Max'].default_value = depth_settings.far_distance
                else:
                    # Auto-range: use very small near and large far
                    map_range.inputs['From Min'].default_value = 0.1
                    map_range.inputs['From Max'].default_value = 1000.0
                
                # CRITICAL FIX: Always invert the output range for proper depth visualization
                map_range.inputs['To Min'].default_value = 1.0
                map_range.inputs['To Max'].default_value = 0.0
                
                # Link render layers Z to map range
                tree.links.new(render_layers.outputs['Depth'], map_range.inputs['Value'])
                
                # 2. Add contrast node to enhance depth differences
                contrast = tree.nodes.new(type='CompositorNodeBrightContrast')
                contrast.name = "DM_Contrast"
                contrast.label = "Enhance Depth Contrast"
                contrast.location = (400, 0)
                # Boost contrast to make depth differences more visible
                contrast.inputs['Contrast'].default_value = 0.2
                # Link map range to contrast
                tree.links.new(map_range.outputs['Value'], contrast.inputs['Image'])
                
                # 3. Color ramp for better visualization (optional but helpful)
                colorramp = tree.nodes.new(type='CompositorNodeValToRGB')
                colorramp.name = "DM_ColorRamp"
                colorramp.label = "Depth Visualization"
                colorramp.location = (600, 0)
                
                # Configure color ramp for good depth visualization
                # Clear existing stops
                if len(colorramp.color_ramp.elements) > 1:
                    colorramp.color_ramp.elements.remove(colorramp.color_ramp.elements[0])
                
                # Add stops for a good grayscale gradient
                colorramp.color_ramp.elements[0].position = 0.0
                colorramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)  # Black for far
                
                # Add white stop for near objects
                newstop = colorramp.color_ramp.elements.new(1.0)
                newstop.color = (1.0, 1.0, 1.0, 1.0)  # White for near
                
                # Link contrast to color ramp
                tree.links.new(contrast.outputs['Image'], colorramp.inputs['Fac'])
                
                # ALWAYS create a Composite node - this fixes the Viewer node error
                composite = tree.nodes.new(type='CompositorNodeComposite')
                composite.name = "DM_Composite"
                composite.label = "Depth Map Output"
                composite.location = (800, -100)  # Position below other output nodes
                tree.links.new(colorramp.outputs[0], composite.inputs['Image'])
                
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
                    tree.links.new(colorramp.outputs[0], viewer.inputs['Image'])
                    
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
                    
                    # Configure for animation-friendly output with frame placeholders
                    # When rendering animation, we need the frame number placeholder
                    if depth_settings.render_animation:
                        # Use format that includes frame numbers: depth_####.png
                        file_output.file_slots[0].path = "depth_"
                        # Enable file format settings for proper animation sequence
                        file_output.format.file_format = 'PNG'  # Using PNG for lossless depth maps
                        # Frame padding for numbering (e.g., ####)
                        # This is handled automatically by Blender's file output node
                    else:
                        # Single frame output doesn't need padding
                        file_output.file_slots[0].path = "depth_"
                        
                    tree.links.new(colorramp.outputs[0], file_output.inputs['Image'])
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
            
            # Update animation settings if needed
            if depth_settings.render_animation:
                # Ensure we have proper animation setup with frame placeholders
                file_output.format.file_format = 'PNG'  # Using PNG for lossless depth maps
            else:
                # Use simple filename for single frame
                file_output.file_slots[0].path = "depth_"


class DEPTHMAP_OT_render(Operator):
    """Renders the depth map or animation sequence"""
    bl_idname = "depthmap.render"
    bl_label = "Render Depth Map"
    bl_description = "Render the depth map with current settings"
    
    def execute(self, context):
        try:
            scene = context.scene
            depth_settings = scene.depth_map_settings
            
            # Only run setup if not already set up or if settings have changed
            if not hasattr(scene, "depth_map_setup_complete") or not scene.depth_map_setup_complete:
                bpy.ops.depthmap.setup()
            
            # Check if animation rendering is enabled
            if (depth_settings.depth_output_method == 'FILE_OUTPUT' and 
                depth_settings.render_animation):
                
                # Store original frame range to restore later
                original_start = scene.frame_start
                original_end = scene.frame_end
                
                # Set frame range if using custom range
                if not depth_settings.use_scene_frame_range:
                    scene.frame_start = depth_settings.frame_start
                    scene.frame_end = depth_settings.frame_end
                
                # Display animation info message
                frame_count = scene.frame_end - scene.frame_start + 1
                output_dir = bpy.path.abspath(depth_settings.output_path)
                
                self.report({'INFO'}, 
                          f"Rendering depth animation: {frame_count} frames to {output_dir}")
                
                # Render animation with current settings
                # Using INVOKE_DEFAULT to show progress to user
                bpy.ops.render.render('INVOKE_DEFAULT', animation=True)
                
                # Note: We don't restore frame range immediately as that would
                # interfere with rendering. Blender will handle the frame range
                # internally during rendering.
                
            else:
                # Render single frame
                self.report({'INFO'}, "Rendering single depth map frame")
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
    
    # Animation properties
    render_animation: BoolProperty(
        name="Render Animation",
        description="Render depth maps for the entire animation sequence",
        default=False
    )
    
    use_scene_frame_range: BoolProperty(
        name="Use Scene Frame Range",
        description="Use the scene's start and end frame settings",
        default=True
    )
    
    frame_start: bpy.props.IntProperty(
        name="Start Frame",
        description="First frame to render in the animation sequence",
        default=1,
        min=0
    )
    
    frame_end: bpy.props.IntProperty(
        name="End Frame",
        description="Last frame to render in the animation sequence",
        default=250,
        min=0
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