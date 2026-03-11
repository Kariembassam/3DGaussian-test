"""Repository-root entrypoint for ComfyUI Manager installs.

Loads node mappings from the bundled node-pack path without relying on a global
`custom_nodes` module import (which may resolve to ComfyUI's parent folder).
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


_ROOT = Path(__file__).resolve().parent
_PACK_DIR = _ROOT / "custom_nodes" / "ComfyUI_4K4D_Manager"
_PACK_INIT = _PACK_DIR / "__init__.py"

if not _PACK_INIT.exists():
    raise FileNotFoundError(f"Expected package init not found: {_PACK_INIT}")

_spec = spec_from_file_location(
    "comfyui_4k4d_manager_pkg",
    _PACK_INIT,
    submodule_search_locations=[str(_PACK_DIR)],
)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Unable to create import spec for {_PACK_INIT}")

_mod = module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

NODE_CLASS_MAPPINGS = _mod.NODE_CLASS_MAPPINGS
NODE_DISPLAY_NAME_MAPPINGS = _mod.NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
