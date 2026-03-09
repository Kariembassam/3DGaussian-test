# 4K4D ComfyUI Node Pack Prototype

Status: Implemented a Runpod-focused ComfyUI custom node pack skeleton under `custom_nodes/ComfyUI_4K4D_Manager` with strict preflight gating, artifact placement helpers, runtime job control, viewer launch hooks, and one-shot workflow JSONs.

See:
- `docs/4k4d_analysis_and_plan.md`
- `docs/4k4d_setup.md`


Manager compatibility note: this repo now exposes a root-level ComfyUI Manager entrypoint (`__init__.py` + `comfyui-manager.json`) so cloning the repo directly into `ComfyUI/custom_nodes` is loadable without extra path surgery.
