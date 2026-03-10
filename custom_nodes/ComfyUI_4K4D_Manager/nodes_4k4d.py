import importlib
import json
import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from .runtime_runner import RuntimeJobRunner


def _to_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


class FourK4DInputIngestNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"input_data_folder": ("STRING", {"default": "./data/input"})}}

    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("dataset_root", "file_count", "summary_json")
    FUNCTION = "run"
    CATEGORY = "4K4D/IO"

    def run(self, input_data_folder: str):
        root = Path(input_data_folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Input folder not found: {root}")
        files = [p for p in root.rglob("*") if p.is_file()]
        summary = {
            "dataset_root": str(root),
            "file_count": len(files),
            "extensions": sorted({p.suffix.lower() for p in files if p.suffix}),
        }
        return str(root), len(files), json.dumps(summary, indent=2)


class FourK4DManifestNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataset_root": ("STRING",),
                "workspace": ("STRING", {"default": "./workspace"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("manifest_path", "manifest_json")
    FUNCTION = "run"
    CATEGORY = "4K4D/IO"

    def run(self, dataset_root: str, workspace: str):
        root = Path(dataset_root).expanduser().resolve()
        ws = Path(workspace).expanduser().resolve()
        ws.mkdir(parents=True, exist_ok=True)
        files = [p for p in root.rglob("*") if p.is_file()]
        manifest = {
            "dataset_root": str(root),
            "num_files": len(files),
            "files": [str(p.relative_to(root)) for p in files],
        }
        path = ws / "dataset_manifest.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return str(path), json.dumps(manifest, indent=2)


class FourK4DEnvBootstrapNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "repo_root": ("STRING", {"default": "./4K4D"}),
                "env_profile": (["runpod_official_comfyui", "custom"],),
                "install_binaries": ("BOOLEAN", {"default": False}),
                "gpu_arch_override": ("STRING", {"default": ""}),
                "dry_run": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("plan_json", "script")
    FUNCTION = "run"
    CATEGORY = "4K4D/Environment"

    def run(self, repo_root: str, env_profile: str, install_binaries: bool, gpu_arch_override: str, dry_run: bool):
        repo = Path(repo_root).expanduser().resolve()
        cmds: List[str] = []
        if gpu_arch_override.strip():
            cmds.append(f'export TORCH_CUDA_ARCH_LIST="{gpu_arch_override.strip()}"')
        cmds.append("python -m pip install --upgrade pip setuptools wheel")
        cmds.append("python -m pip install -r requirements.txt")
        cmds.append("python -m pip install -e .")
        if env_profile == "custom" and install_binaries:
            cmds.insert(0, "sudo apt-get update && sudo apt-get install -y ffmpeg git")
        plan = {
            "env_profile": env_profile,
            "repo_root": str(repo),
            "install_binaries": bool(install_binaries),
            "gpu_arch_override": gpu_arch_override,
            "dry_run": bool(dry_run),
            "commands": cmds,
        }
        if not dry_run:
            for c in cmds:
                os.system(f"cd {repo} && {c}")
        return json.dumps(plan, indent=2), "\n".join([f"cd {repo}"] + cmds)


class FourK4DEnvCheckNode:
    REQUIRED_BINARIES = ["python", "git"]
    REQUIRED_MODULES = ["torch", "numpy"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "workspace": ("STRING", {"default": "./workspace"}),
                "bootstrap_plan_json": ("STRING", {"default": ""}),
                "extra_binaries_csv": ("STRING", {"default": ""}),
                "extra_modules_csv": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("all_ok", "report_path", "report_json")
    FUNCTION = "run"
    CATEGORY = "4K4D/Environment"

    def run(self, workspace: str, bootstrap_plan_json: str, extra_binaries_csv: str, extra_modules_csv: str):
        ws = Path(workspace).expanduser().resolve()
        ws.mkdir(parents=True, exist_ok=True)
        bins = self.REQUIRED_BINARIES + [b.strip() for b in extra_binaries_csv.split(",") if b.strip()]
        mods = self.REQUIRED_MODULES + [m.strip() for m in extra_modules_csv.split(",") if m.strip()]
        bootstrap_plan_valid = True
        if bootstrap_plan_json.strip():
            try:
                plan = json.loads(bootstrap_plan_json)
                bootstrap_plan_valid = isinstance(plan, dict) and "commands" in plan
            except Exception:
                bootstrap_plan_valid = False
        bin_checks = {b: shutil.which(b) is not None for b in bins}
        mod_checks = {}
        for m in mods:
            try:
                importlib.import_module(m)
                mod_checks[m] = True
            except Exception:
                mod_checks[m] = False
        all_ok = all(bin_checks.values()) and all(mod_checks.values()) and bootstrap_plan_valid
        report = {
            "all_ok": all_ok,
            "bootstrap_plan_valid": bootstrap_plan_valid,
            "binary_checks": bin_checks,
            "module_checks": mod_checks,
        }
        report_path = ws / "env_check_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return all_ok, str(report_path), json.dumps(report, indent=2)


class FourK4DArtifactResolverNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"model_preset": ("STRING", {"default": "4k4d_base"})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("artifact_json",)
    FUNCTION = "run"
    CATEGORY = "4K4D/Artifacts"

    def run(self, model_preset: str):
        registry_path = Path(__file__).parent / "model_registry.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if model_preset not in registry:
            raise ValueError(f"Unknown model_preset: {model_preset}")
        return (json.dumps(registry[model_preset], indent=2),)


class FourK4DArtifactDownloadNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "artifact_json": ("STRING",),
                "workspace": ("STRING", {"default": "./workspace"}),
                "dry_run": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("artifact_path", "log")
    FUNCTION = "run"
    CATEGORY = "4K4D/Artifacts"

    def run(self, artifact_json: str, workspace: str, dry_run: bool):
        art = json.loads(artifact_json)
        ws = Path(workspace).expanduser().resolve()
        ws.mkdir(parents=True, exist_ok=True)
        target = ws / art["target_relpath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if dry_run:
            return str(target), f"DRY RUN: would download {art['url']} to {target}"
        if target.exists() and target.stat().st_size > 0:
            return str(target), f"Model already present at {target}, skipping download"
        urllib.request.urlretrieve(art["url"], target)
        return str(target), f"Downloaded {art['url']} to {target}"


class FourK4DArtifactManualNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"workspace": ("STRING", {"default": "./workspace"}), "instructions": ("STRING", {"multiline": True, "default": "Place required checkpoints under workspace/artifacts"})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("instruction_file",)
    FUNCTION = "run"
    CATEGORY = "4K4D/Artifacts"

    def run(self, workspace: str, instructions: str):
        ws = Path(workspace).expanduser().resolve()
        ws.mkdir(parents=True, exist_ok=True)
        path = ws / "manual_artifact_instructions.txt"
        path.write_text(instructions, encoding="utf-8")
        return (str(path),)


class FourK4DCommandBuilderNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "repo_root": ("STRING",),
                "workspace": ("STRING",),
                "manifest_path": ("STRING",),
                "artifact_path": ("STRING",),
                "extra_args": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("command",)
    FUNCTION = "run"
    CATEGORY = "4K4D/Pipeline"

    def run(self, repo_root: str, workspace: str, manifest_path: str, artifact_path: str, extra_args: str):
        cmd = (
            f"cd {Path(repo_root).expanduser().resolve()} && "
            f"python train.py --workspace {workspace} --manifest {manifest_path} --checkpoint {artifact_path} {extra_args}".strip()
        )
        return (cmd,)


class FourK4DLaunchCommandNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "command": ("STRING",),
                "workspace": ("STRING", {"default": "./workspace"}),
                "require_env_ok": ("BOOLEAN", {"default": True}),
                "env_ok": ("BOOLEAN", {"default": False}),
                "dry_run": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("job_id", "message")
    FUNCTION = "run"
    CATEGORY = "4K4D/Pipeline"

    def run(self, command: str, workspace: str, require_env_ok: bool, env_ok: bool, dry_run: bool):
        if _to_bool(require_env_ok) and not _to_bool(env_ok):
            raise RuntimeError("Launch blocked: require_env_ok=true and env_ok=false")
        if _to_bool(dry_run):
            return "dry_run", f"DRY RUN: would launch `{command}`"
        runner = RuntimeJobRunner(workspace)
        state = runner.launch(command=command, cwd=str(Path(workspace).expanduser().resolve()))
        return state.job_id, f"Launched job {state.job_id}"


class FourK4DPollNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"workspace": ("STRING", {"default": "./workspace"}), "job_id": ("STRING",)}}

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("status", "state_json")
    FUNCTION = "run"
    CATEGORY = "4K4D/Pipeline"

    def run(self, workspace: str, job_id: str):
        if job_id == "dry_run":
            return "dry_run", json.dumps({"job_id": job_id, "status": "dry_run"}, indent=2)
        runner = RuntimeJobRunner(workspace)
        state = runner.poll(job_id)
        return state.status, json.dumps(state.__dict__, indent=2)


class FourK4DStopNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"workspace": ("STRING", {"default": "./workspace"}), "job_id": ("STRING",)}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("state_json",)
    FUNCTION = "run"
    CATEGORY = "4K4D/Pipeline"

    def run(self, workspace: str, job_id: str):
        runner = RuntimeJobRunner(workspace)
        state = runner.stop(job_id)
        return (json.dumps(state.__dict__, indent=2),)


class FourK4DViewerLaunchNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "repo_root": ("STRING",),
                "workspace": ("STRING",),
                "port": ("INT", {"default": 8890, "min": 1, "max": 65535}),
                "require_env_ok": ("BOOLEAN", {"default": True}),
                "env_ok": ("BOOLEAN", {"default": False}),
                "dry_run": ("BOOLEAN", {"default": True}),
                "processing_job_id": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("job_id", "viewer_url")
    FUNCTION = "run"
    CATEGORY = "4K4D/Viewer"

    def run(self, repo_root: str, workspace: str, port: int, require_env_ok: bool, env_ok: bool, dry_run: bool, processing_job_id: str):
        if _to_bool(require_env_ok) and not _to_bool(env_ok):
            raise RuntimeError("Viewer launch blocked: require_env_ok=true and env_ok=false")
        cmd = f"cd {Path(repo_root).expanduser().resolve()} && python viewer.py --workspace {workspace} --port {port}"
        if _to_bool(dry_run):
            return "dry_run", f"http://127.0.0.1:{port}"
        runner = RuntimeJobRunner(workspace)
        state = runner.launch(command=cmd, cwd=str(Path(workspace).expanduser().resolve()))
        return state.job_id, f"http://127.0.0.1:{port}"


class FourK4DViewerPollNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"workspace": ("STRING", {"default": "./workspace"}), "job_id": ("STRING",)}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "run"
    CATEGORY = "4K4D/Viewer"

    def run(self, workspace: str, job_id: str):
        if job_id == "dry_run":
            return ("dry_run",)
        runner = RuntimeJobRunner(workspace)
        state = runner.poll(job_id)
        return (state.status,)


NODE_CLASS_MAPPINGS = {
    "FourK4D_InputIngest": FourK4DInputIngestNode,
    "FourK4D_ManifestGenerate": FourK4DManifestNode,
    "FourK4D_EnvBootstrap": FourK4DEnvBootstrapNode,
    "FourK4D_EnvCheck": FourK4DEnvCheckNode,
    "FourK4D_ArtifactResolve": FourK4DArtifactResolverNode,
    "FourK4D_ArtifactDownload": FourK4DArtifactDownloadNode,
    "FourK4D_ArtifactManualFallback": FourK4DArtifactManualNode,
    "FourK4D_CommandBuilder": FourK4DCommandBuilderNode,
    "FourK4D_LaunchCommand": FourK4DLaunchCommandNode,
    "FourK4D_Poll": FourK4DPollNode,
    "FourK4D_Stop": FourK4DStopNode,
    "FourK4D_ViewerLaunch": FourK4DViewerLaunchNode,
    "FourK4D_ViewerPoll": FourK4DViewerPollNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {k: k.replace("FourK4D_", "4K4D ").replace("_", " ") for k in NODE_CLASS_MAPPINGS}
