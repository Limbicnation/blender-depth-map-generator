# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

**Blender Depth Map Generator** is a Blender addon written in Python that automates depth map (Z-depth) creation and rendering. The addon provides a clean UI in Blender's 3D Viewport sidebar for generating depth maps from 3D scenes, with support for both single frame and animation sequence rendering.

- **Version**: 1.2
- **License**: Apache License 2.0
- **Minimum Blender Version**: 3.0.0
- **Language**: English (all documentation and code comments)

## Project Structure

```
blender-depth-map-generator/
├── depth_map_generator.py    # Main addon file (single file, self-contained)
├── README.md                 # Human-readable project documentation
├── CLAUDE.md                 # Claude Code specific guidance
├── GEMINI.md                 # Gemini specific guidance
├── AGENTS.md                 # This file - general agent guidance
├── LICENSE                   # Apache 2.0 license
├── .gitignore                # Python standard gitignore
├── .env                      # Environment variables (GEMINI_API_KEY)
├── images/                   # Project images and screenshots
│   ├── depth-map-icon.svg
│   ├── depth-ui-round-corners.png
│   └── blender-depth-render-ui-*.png
└── .github/
    └── workflows/            # GitHub Actions CI/CD workflows
        ├── claude.yml
        ├── claude-code-review.yml
        ├── gemini-cli.yml
        ├── gemini-pr-review.yml
        ├── gemini-issue-automated-triage.yml
        └── gemini-issue-scheduled-triage.yml
```

## Technology Stack

- **Language**: Python 3.x
- **Platform**: Blender 3.0+ Python API (bpy)
- **Dependencies**: Only Blender's built-in Python API (bpy, os)
- **No external package managers**: No pip, npm, cargo, etc.

## Architecture

### Single-File Addon Structure

The entire addon is contained in a single Python file (`depth_map_generator.py`) following Blender's addon conventions:

```python
bl_info = {...}  # Addon metadata dictionary

# Classes (in order of registration dependency):
# 1. PropertyGroup - stores settings
# 2. Operators - actions the user can trigger
# 3. Panels - UI layout

# Registration functions:
def register()
def unregister()

if __name__ == "__main__":
    register()
```

### Core Components

| Class | Type | Purpose |
|-------|------|---------|
| `DepthMapSettings` | `PropertyGroup` | Stores all addon settings (depth range, output method, animation settings) |
| `DEPTHMAP_PT_main_panel` | `Panel` | Main UI panel in 3D Viewport sidebar under "Depth Map" tab |
| `DEPTHMAP_OT_setup` | `Operator` | Configures render passes and compositing nodes for depth map generation |
| `DEPTHMAP_OT_render` | `Operator` | Handles both single frame and animation sequence rendering |
| `DEPTHMAP_OT_reset` | `Operator` | Cleans up compositing nodes and restores default setup |

### Compositing Pipeline

The addon creates a sophisticated compositing node tree with these nodes:

1. **DM_RenderLayers** (`CompositorNodeRLayers`) - Sources the Z-pass depth data
2. **DM_RangeMapper** (`CompositorNodeMapRange`) - Converts depth values to 0-1 range with inversion (far=0, near=1)
3. **DM_Contrast** (`CompositorNodeBrightContrast`) - Enhances depth differences for better visualization
4. **DM_ColorRamp** (`CompositorNodeValToRGB`) - Provides grayscale gradient for depth visualization
5. **Output nodes** - Composite, Viewer, or FileOutput depending on user selection

### Node Naming Convention

All depth map nodes use the `DM_` prefix for easy identification and management:
- `DM_RenderLayers`
- `DM_RangeMapper`
- `DM_Contrast`
- `DM_ColorRamp`
- `DM_Composite`
- `DM_Viewer`
- `DM_FileOutput`

## Code Style Guidelines

### Blender Addon Conventions

1. **Class Naming**: Use uppercase prefixes for class types:
   - `DEPTHMAP_OT_*` for Operators
   - `DEPTHMAP_PT_*` for Panels
   - `DepthMapSettings` for PropertyGroups (PascalCase)

2. **bl_idname Format**: `{category}.{operation}` (lowercase)
   - Example: `depthmap.setup`, `depthmap.render`, `depthmap.reset`

3. **Documentation Strings**: All classes have docstrings describing their purpose

4. **Property Definitions**: Use type annotations via `bpy.props`:
   ```python
   near_distance: FloatProperty(...)
   use_custom_range: BoolProperty(...)
   ```

### Python Style

- Follow PEP 8 style guide
- Use descriptive variable names
- Include error handling with try-catch blocks
- Use f-strings for string formatting
- Indentation: 4 spaces

### Error Handling

All operators implement comprehensive error handling:

```python
def execute(self, context):
    try:
        # Operation logic
        self.report({'INFO'}, "Success message")
        return {'FINISHED'}
    except Exception as e:
        self.report({'ERROR'}, f"Operation failed: {str(e)}")
        return {'CANCELLED'}
```

## Development Workflow

### Testing

- **No automated test suite**: This is a Blender addon that requires Blender's runtime environment
- **Manual testing**: Install in Blender and test UI interactions
- **Test scenarios**:
  1. Fresh install and enable addon
  2. Setup depth map with each output method (Composite, Viewer, File Output)
  3. Render single frame depth map
  4. Render animation sequence
  5. Reset and verify cleanup
  6. Update settings and verify node updates

### Build Process

There is no build process. The addon is distributed as a single Python file:

1. Install via Blender → Edit → Preferences → Add-ons → Install
2. Select `depth_map_generator.py`
3. Enable the addon

### Release Process

1. Update version in `bl_info` dictionary:
   ```python
   "version": (major, minor),
   ```
2. Update CHANGELOG (if applicable)
3. Tag release in Git
4. Users download and install the `.py` file directly

## CI/CD Configuration

### GitHub Actions Workflows

This repository uses multiple AI-powered GitHub Actions workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `claude.yml` | `@claude` mention in comments/issues | Interactive Claude Code assistance |
| `claude-code-review.yml` | PR open/synchronize | Automated Claude PR review |
| `gemini-cli.yml` | `@gemini-cli` mention | Interactive Gemini CLI assistance |
| `gemini-pr-review.yml` | PR open or `@gemini-cli /review` | Automated Gemini PR review |
| `gemini-issue-automated-triage.yml` | Issue open | Auto-label new issues |
| `gemini-issue-scheduled-triage.yml` | Scheduled | Periodic issue triage |

### Required Secrets/Variables

- `CLAUDE_CODE_OAUTH_TOKEN` - For Claude Code integration
- `GEMINI_API_KEY` - For Gemini CLI integration (also in `.env` for local use)
- `GCP_WIF_PROVIDER`, `GOOGLE_CLOUD_PROJECT`, etc. - For GCP/Vertex AI integration

## Security Considerations

1. **No external network calls**: The addon only uses Blender's internal API
2. **File system access**: Limited to user-specified output paths via `bpy.path.abspath()`
3. **Directory creation**: Uses `os.makedirs(output_dir, exist_ok=True)` for output directories
4. **No sensitive data in code**: API keys are stored in `.env` (gitignored) and GitHub Secrets

## Key Implementation Details

### Setup Tracking

Uses `scene.depth_map_setup_complete` boolean property to track configuration state:
- Prevents unnecessary node recreation
- Allows updating existing nodes when settings change
- Used for UI feedback (checkmark indicator)

### Animation Handling

Supports both scene frame range and custom frame ranges:
- When `use_scene_frame_range=True`: Uses `scene.frame_start` and `scene.frame_end`
- When `use_scene_frame_range=False`: Uses custom `frame_start` and `frame_end` properties

### Path Management

- Default output path: `//depth_maps/` (Blender project-relative)
- Supports both absolute paths and Blender's `//` prefix for relative paths
- Automatic directory creation with `os.makedirs()`

### Output Formats

- **File Output**: PNG format, BW color mode, 8-bit depth
- **Animation sequences**: Frame numbering format `depth_####.png`
- **Single frame**: Named `depth_map.png`

## Common Tasks

### Adding a New Setting

1. Add property to `DepthMapSettings` class
2. Add UI element in `DEPTHMAP_PT_main_panel.draw()`
3. Handle in `DEPTHMAP_OT_setup.execute()`
4. Update in `DEPTHMAP_OT_setup._update_node_settings()` if needed

### Adding a New Output Method

1. Add enum item to `depth_output_method` property
2. Add handling in setup operator's output configuration section
3. Update render operator if needed
4. Update documentation

### Modifying Node Setup

1. Locate node by name in `execute()` or `_update_node_settings()`
2. Apply changes to node properties
3. Ensure `DM_` naming convention is maintained
4. Test both fresh setup and update scenarios

## References

- [Blender Python API Documentation](https://docs.blender.org/api/current/)
- [Blender Addon Tutorial](https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html)
- [CLAUDE.md](./CLAUDE.md) - Detailed Claude-specific guidance
- [GEMINI.md](./GEMINI.md) - Detailed Gemini-specific guidance
