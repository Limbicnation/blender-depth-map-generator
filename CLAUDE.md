# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Blender addon written in Python that automates depth map (Z-depth) creation and rendering. The addon provides a clean UI in Blender's 3D Viewport sidebar for generating depth maps from 3D scenes, with support for both single frame and animation sequence rendering.

## Architecture

The addon follows standard Blender addon architecture with these key components:

### Core Classes

- `DEPTHMAP_PT_main_panel` - Main UI panel in the 3D Viewport sidebar under "Depth Map" tab
- `DEPTHMAP_OT_setup` - Operator that configures render passes and compositing nodes for depth map generation
- `DEPTHMAP_OT_render` - Operator that handles both single frame and animation sequence rendering
- `DEPTHMAP_OT_reset` - Operator that cleans up compositing nodes and resets to default state
- `DepthMapSettings` - Property group storing all addon settings (depth range, output method, animation settings)

### Compositing Pipeline

The addon creates a sophisticated compositing node tree:
1. **RenderLayers node** (`DM_RenderLayers`) - Sources the Z-pass depth data
2. **MapRange node** (`DM_RangeMapper`) - Converts depth values to 0-1 range with inversion (far=0, near=1)
3. **BrightContrast node** (`DM_Contrast`) - Enhances depth differences for better visualization
4. **ColorRamp node** (`DM_ColorRamp`) - Provides grayscale gradient for depth visualization
5. **Output nodes** - Composite, Viewer, or FileOutput depending on user selection

### Key Features

- **Automatic Setup**: One-click configuration of Z-pass and compositing nodes
- **Multiple Output Methods**: Composite output, Viewer node preview, or file export
- **Animation Support**: Render entire animation sequences as depth maps with frame numbering
- **Custom Depth Range**: User-configurable near/far distances for depth mapping
- **Smart Node Management**: Uses descriptive node names and preserves existing setups when possible

## Development Notes

### File Structure
- `depth_map_generator.py` - Single file containing the entire addon
- Standard Blender addon structure with `bl_info` dictionary for metadata
- Uses Blender's property system for persistent settings storage

### Key Implementation Details

- **Node Naming Convention**: All depth map nodes use "DM_" prefix for easy identification
- **Setup Tracking**: Uses `scene.depth_map_setup_complete` property to track configuration state
- **Animation Handling**: Supports both scene frame range and custom frame ranges
- **Path Management**: Creates output directories automatically and handles relative paths
- **Error Handling**: Comprehensive try-catch blocks with user-friendly error reporting

### Blender Integration

- **Panel Location**: 3D Viewport → Sidebar (N-panel) → "Depth Map" tab
- **Operator Registration**: All operators registered with proper `bl_idname` and descriptions
- **Property Integration**: Settings stored as scene properties for persistence across sessions
- **Icon Usage**: Leverages Blender's built-in icons for UI consistency

### Output Formats

- **File Output**: PNG format for lossless depth maps
- **Animation Sequences**: Automatic frame numbering (depth_####.png)
- **Path Handling**: Supports both absolute and relative paths (// prefix for project-relative)

## Installation and Usage

1. Install as standard Blender addon via Preferences → Add-ons → Install
2. Access through 3D Viewport sidebar under "Depth Map" tab
3. Click "Setup Depth Map" to configure compositing
4. Adjust settings and choose output method
5. Use "Render Depth Map" or "Render Depth Animation" as needed

## Code Conventions

- Follow Blender's addon naming conventions (UPPERCASE_OT/PT_ prefixes)
- Use descriptive node names with "DM_" prefix for organization
- Implement proper error handling with user-visible messages
- Maintain compatibility with Blender 3.0+
- Use property groups for organized settings storage