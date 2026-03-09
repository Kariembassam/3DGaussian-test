"""Repository-root entrypoint for ComfyUI Manager installs.

ComfyUI Manager clones this repository directly into ComfyUI/custom_nodes/<repo>.
Having a root __init__.py makes the repo itself load as a custom node package.
"""

from custom_nodes.ComfyUI_4K4D_Manager import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
