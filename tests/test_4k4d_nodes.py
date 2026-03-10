import importlib.util
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_nodes.ComfyUI_4K4D_Manager.nodes_4k4d import (
    NODE_CLASS_MAPPINGS,
    FourK4DArtifactDownloadNode,
    FourK4DArtifactResolverNode,
    FourK4DCommandBuilderNode,
    FourK4DEnvBootstrapNode,
    FourK4DEnvCheckNode,
    FourK4DInputIngestNode,
    FourK4DLaunchCommandNode,
    FourK4DManifestNode,
    FourK4DPollNode,
    FourK4DStopNode,
    FourK4DViewerLaunchNode,
)


def test_manifest_data_ingest():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "input"
        root.mkdir()
        (root / "a.txt").write_text("x", encoding="utf-8")
        ingest = FourK4DInputIngestNode()
        ds_root, count, _ = ingest.run(str(root))
        assert count == 1
        mani = FourK4DManifestNode()
        path, mani_json = mani.run(ds_root, str(Path(td) / "ws"))
        assert Path(path).exists()
        assert json.loads(mani_json)["num_files"] == 1


def test_bootstrap_dry_run_output():
    node = FourK4DEnvBootstrapNode()
    plan_json, script = node.run(".", "runpod_official_comfyui", False, "8.9", True)
    plan = json.loads(plan_json)
    assert plan["dry_run"] is True
    assert "TORCH_CUDA_ARCH_LIST" in script


def test_env_check_report_structure():
    with tempfile.TemporaryDirectory() as td:
        node = FourK4DEnvCheckNode()
        all_ok, report_path, report_json = node.run(td, "python", "json")
        report = json.loads(report_json)
        assert Path(report_path).exists()
        assert "binary_checks" in report and "module_checks" in report
        assert isinstance(all_ok, bool)


def test_artifact_dry_run_and_placement_behavior():
    with tempfile.TemporaryDirectory() as td:
        resolver = FourK4DArtifactResolverNode()
        art_json = resolver.run("4k4d_base")[0]
        dl = FourK4DArtifactDownloadNode()
        artifact_path, log = dl.run(art_json, td, True)
        assert "DRY RUN" in log
        assert artifact_path.endswith("4k4d_base.ckpt")


def test_runtime_launch_poll_stop_semantics():
    with tempfile.TemporaryDirectory() as td:
        launch = FourK4DLaunchCommandNode()
        job_id, _ = launch.run("python -c 'import time; time.sleep(3)'", td, False, False, False)
        poll = FourK4DPollNode()
        status, _ = poll.run(td, job_id)
        assert status in {"running", "finished"}
        stop = FourK4DStopNode()
        state_json = stop.run(td, job_id)[0]
        assert json.loads(state_json)["status"] in {"stopped", "finished"}


def test_viewer_node_command_generation_launch_behavior():
    with tempfile.TemporaryDirectory() as td:
        node = FourK4DViewerLaunchNode()
        job_id, url = node.run(".", td, 8890, True, True, True)
        assert job_id == "dry_run"
        assert url.endswith(":8890")


def test_workflow_class_types_exist_and_main_connectivity():
    wf_dir = Path("custom_nodes/ComfyUI_4K4D_Manager/workflows")
    for wf in wf_dir.glob("*.json"):
        data = json.loads(wf.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            assert node["type"] in NODE_CLASS_MAPPINGS
    main = json.loads((wf_dir / "99_main_one_shot_pipeline.json").read_text(encoding="utf-8"))
    ids = {n["id"] for n in main["nodes"]}
    assert any(n["type"] == "FourK4D_LaunchCommand" for n in main["nodes"])
    assert any(n["type"] == "FourK4D_EnvCheck" for n in main["nodes"])
    assert len(main.get("links", [])) > 0
    for link in main.get("links", []):
        assert link[1] in ids and link[3] in ids


def test_root_manager_manifest_exists_and_points_to_entry():
    manifest = Path("comfyui-manager.json")
    assert manifest.exists()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data.get("entry") == "__init__.py"
    assert Path("__init__.py").exists()


def test_dns_diagnostic_script_present_and_executable():
    script = Path("scripts/diagnose_github_connectivity.sh")
    assert script.exists()
    mode = script.stat().st_mode
    assert mode & 0o111


def test_root_entrypoint_loads_node_mappings_via_local_package_path():
    init_py = Path("__init__.py").resolve()
    spec = importlib.util.spec_from_file_location("repo_entry", init_py)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "FourK4D_EnvCheck" in mod.NODE_CLASS_MAPPINGS
