# Technical Review — [majestic-swimming-hollerith.md](file://wsl.localhost/Ubuntu-24.04/home/gero/.claude/plans/majestic-swimming-hollerith.md) Project Plan

> Review conducted against the **python-development-python-scaffold** skill and the current state of the [blender-depth-map-generator](file:///\\wsl.localhost\Ubuntu-24.04\home\gero\GitHub\python-experiments\blender-depth-map-generator) repository.

---

## 1. Executive Summary

The plan correctly diagnoses the **root cause** of the Windows `[WinError 2]` — stale README instructions pointing users to the v1.x single-file [depth_map_generator.py](file://wsl.localhost/Ubuntu-24.04/home/gero/GitHub/python-experiments/blender-depth-map-generator/depth_map_generator.py) when the addon is now a multi-file package. The three proposed changes (README update, `build_zip.py`, temp-file cleanup) are **well-scoped**, **low-risk**, and will resolve the immediate issue.

However, evaluated against modern Python scaffolding standards, several **structural gaps and improvement opportunities** exist in both the plan and the broader project. These are detailed below.

---

## 2. Scorecard

| Dimension | Rating | Notes |
|---|:---:|---|
| **Problem Diagnosis** | ✅ Excellent | Clear root-cause analysis with error text |
| **Scope Control** | ✅ Excellent | Tightly scoped; optional follow-ups deferred |
| **README Remediation** | ✅ Good | Correct zip-based workflow |
| **Build Tooling** | ⚠️ Adequate | `build_zip.py` works but is minimal |
| **Packaging Standards** | ❌ Missing | No `pyproject.toml`, no build system |
| **Testing & Verification** | ⚠️ Weak | Manual-only verification plan |
| **CI/CD Integration** | ❌ Not addressed | Six GH Actions workflows exist, none leveraged |
| **Blender 4.2+ Compat** | ⚠️ Deferred | `blender_manifest.toml` explicitly punted |
| **Linting / Quality** | ❌ Missing | No ruff/mypy/flake8 configuration |

---

## 3. Detailed Findings

### 3.1 Scaffolding Strategy

> [!IMPORTANT]
> **No `pyproject.toml` exists anywhere in the project.**

The python-scaffold skill mandates `pyproject.toml` as the canonical project metadata file for all Python projects, even those that are not PyPI packages. For a Blender addon, `pyproject.toml` serves as the single source of truth for:

- **Project metadata** (name, version, authors, license) — currently duplicated in `bl_info` inside [**init**.py](file://wsl.localhost/Ubuntu-24.04/home/gero/GitHub/python-experiments/blender-depth-map-generator/depth_map_generator/__init__.py)
- **Dev dependencies** (ruff, mypy, pytest)
- **Tool configuration** (ruff rules, pytest paths, mypy settings)
- **Build system** declaration (even if it's `hatchling` with no PyPI publishing)

**Recommendation:** Add a `pyproject.toml` at the project root with at least:

```toml
[project]
name = "blender-depth-map-generator"
version = "2.0.0"
description = "Blender addon for depth map and alpha mask rendering"
requires-python = ">=3.10"  # Blender 3.x+ ships Python 3.10+
license = {text = "Apache-2.0"}
authors = [{name = "Gero Doll"}]

[project.optional-dependencies]
dev = ["ruff>=0.2.0", "mypy>=1.8.0"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
