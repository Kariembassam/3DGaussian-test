# 4K4D Setup Guide (Runpod Official ComfyUI)

## Required binaries
- python
- git

## Required Python modules
- torch
- numpy

## Install steps
1. Clone/copy this node pack into `custom_nodes/ComfyUI_4K4D_Manager`.
2. Restart ComfyUI.
3. Open `workflows/10_4k4d_bootstrap_validate.json`.
4. Run `4K4D EnvBootstrap` in `dry_run=true` to inspect commands.
5. Set `dry_run=false` and execute bootstrap.
6. Run `4K4D EnvCheck` and confirm `all_ok=true`.
7. Open `99_main_one_shot_pipeline.json` and set:
   - repo root
   - workspace
   - model preset
   - input data folder
   - env profile
   - dry_run toggles
   - gpu arch override (if needed)

## Troubleshooting matrix
- Env check fails (binary): add binary to PATH or install in container image.
- Env check fails (module): install module with pip in active ComfyUI environment.
- Native extension build failure: set `gpu_arch_override` (e.g., `8.9`) and reinstall.
- Artifact download failure: use manual fallback node and place checkpoint in expected path.
- Launch blocked: `require_env_ok=true` with failed preflight; rerun EnvCheck after fixes.

## Automation boundary
Automated:
- Command planning/bootstrap
- Preflight report
- Artifact fetch planning/download
- Runtime job launch/poll/stop

External/manual (current):
- Confirming authoritative model download URLs
- Repo-specific CLI tuning for each dataset/config variant

## ComfyUI Manager install error: `git clone ... exit code 128`
Typical causes and fixes:
- Repository is private or inaccessible from the Runpod container Git context. Make repo public or use a token-enabled URL in Manager.
- URL typo or wrong owner/repo name. Verify by running `git ls-remote <repo_url>` from the container.
- Missing `.git` suffix can fail for some setups/proxies; prefer full URL `https://github.com/<owner>/<repo>.git`.
- Rate limit / auth prompt disabled in non-interactive mode. Use PAT in URL or pre-configured git credentials.

This repository now includes a **root-level `__init__.py` + `comfyui-manager.json`** so that once clone succeeds, ComfyUI Manager can load it directly as a node pack.
