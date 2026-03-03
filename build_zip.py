#!/usr/bin/env python3
"""Build the Blender addon zip for distribution."""
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
PACKAGE = ROOT / "depth_map_generator"
OUTPUT = ROOT / "depth_map_generator.zip"

with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(PACKAGE.rglob("*.py")):
        arcname = path.relative_to(ROOT)
        zf.write(path, arcname)

print(f"Created {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
