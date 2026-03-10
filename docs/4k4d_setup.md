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


## Runpod DNS failure: `Could not resolve host: github.com`
This error means your pod cannot resolve DNS for GitHub, so clone/install fails before ComfyUI node code is even loaded.

### Quick diagnostics
Run:
```bash
bash scripts/diagnose_github_connectivity.sh
```

### Recovery steps (Runpod)
1. Restart the pod/container (many transient DNS issues clear after restart).
2. Verify outbound network for the pod template/firewall/VPC policy.
3. Check resolver config in `/etc/resolv.conf` (nameserver must be reachable).
4. If your environment allows, set public DNS servers temporarily:
   ```bash
   printf "nameserver 1.1.1.1
nameserver 8.8.8.8
" > /etc/resolv.conf
   ```
5. Retry clone using full URL:
   ```bash
   git clone https://github.com/Kariembassam/3DGaussian-test.git
   ```

### No-network fallback
If your pod has no outbound internet, upload this repository as a zip/tar from your local machine into `ComfyUI/custom_nodes`, extract it, and restart ComfyUI.


## Workflow shows `This workflow has missing nodes` after install
If workflows list `FourK4D_*` as missing right after install:
1. Pull/update to the latest commit that includes the root loader fix.
2. Restart ComfyUI fully (not just browser refresh).
3. In ComfyUI Manager, click "Rescan custom nodes".
4. Reopen the workflow JSON.

Why this happened: older loader logic could import from the wrong `custom_nodes` namespace path in some ComfyUI layouts. The root loader now uses local package-path loading to avoid namespace collisions.
