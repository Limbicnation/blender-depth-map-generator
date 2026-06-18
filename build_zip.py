#!/usr/bin/env python3
"""Build the Blender addon zip for distribution."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
PACKAGE = ROOT / "depth_map_generator"
OUTPUT = ROOT / "depth_map_generator.zip"

with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
    # Write blender_manifest.toml to the root of the zip
    zf.write(ROOT / "blender_manifest.toml", "blender_manifest.toml")
    
    # Write Python files flat to the root of the zip
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        arcname = path.relative_to(PACKAGE)
        zf.write(path, arcname)

print(f"Created {OUTPUT} ({OUTPUT.stat().st_size} bytes)")

