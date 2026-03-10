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
        all_ok, report_path, report_json = node.run(td, "{\"commands\":[\"x\"]}", "python", "json")
        report = json.loads(report_json)
        assert Path(report_path).exists()
        assert "binary_checks" in report and "module_checks" in report and "bootstrap_plan_valid" in report
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
        job_id, url = node.run(".", td, 8890, True, True, True, "")
        assert job_id == "dry_run"
        assert url.endswith(":8890")


def test_workflow_class_types_exist_and_connectivity():
    wf_dir = Path("custom_nodes/ComfyUI_4K4D_Manager/workflows")
    workflow_files = sorted(wf_dir.glob("*.json"))
    assert workflow_files

    for wf in workflow_files:
        data = json.loads(wf.read_text(encoding="utf-8"))
        ids = {n["id"] for n in data.get("nodes", [])}
        for node in data.get("nodes", []):
            assert node["type"] in NODE_CLASS_MAPPINGS

        # all shipped workflows must be connected and visually grouped
        assert len(data.get("links", [])) > 0
        assert len(data.get("groups", [])) > 0
        for link in data.get("links", []):
            assert link[1] in ids and link[3] in ids

    main = json.loads((wf_dir / "99_main_one_shot_pipeline.json").read_text(encoding="utf-8"))
    node_types = {n["type"] for n in main["nodes"]}
    required = {
        "FourK4D_InputIngest",
        "FourK4D_ManifestGenerate",
        "FourK4D_EnvBootstrap",
        "FourK4D_EnvCheck",
        "FourK4D_ArtifactResolve",
        "FourK4D_ArtifactDownload",
        "FourK4D_CommandBuilder",
        "FourK4D_LaunchCommand",
        "FourK4D_Poll",
        "FourK4D_ViewerLaunch",
        "FourK4D_ViewerPoll",
    }
    assert required.issubset(node_types)


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


def test_model_registry_targets_runpod_comfyui_path():
    data = json.loads(Path("custom_nodes/ComfyUI_4K4D_Manager/model_registry.json").read_text(encoding="utf-8"))
    assert data["4k4d_base"]["target_relpath"] == "models/checkpoints/4k4d/4k4d_base.ckpt"
    assert "example.com" not in data["4k4d_base"]["url"]
    assert data["4k4d_base"]["url"].startswith("https://github.com/zju3dv/4K4D/releases/download/")
    assert data["4k4d_base"]["alternate_urls"]


def test_main_workflow_is_automated_by_default_except_input_folder():
    wf = Path("custom_nodes/ComfyUI_4K4D_Manager/workflows/99_main_one_shot_pipeline.json")
    data = json.loads(wf.read_text(encoding="utf-8"))
    by_type = {n["type"]: n for n in data["nodes"]}

    assert by_type["FourK4D_InputIngest"]["widgets_values"][0].endswith("/input/video_folder")
    assert by_type["FourK4D_ArtifactDownload"]["widgets_values"][2] is False
    assert by_type["FourK4D_EnvBootstrap"]["widgets_values"][4] is False
    assert by_type["FourK4D_LaunchCommand"]["widgets_values"][4] is False
    assert by_type["FourK4D_ViewerLaunch"]["widgets_values"][5] is False


def test_root_workflows_exist_and_are_connected():
    root_wf_dir = Path("workflows")
    pkg_wf_dir = Path("custom_nodes/ComfyUI_4K4D_Manager/workflows")
    root_files = sorted([f.name for f in root_wf_dir.glob("*.json")])
    pkg_files = sorted([f.name for f in pkg_wf_dir.glob("*.json")])
    assert root_files == pkg_files

    for name in root_files:
        data = json.loads((root_wf_dir / name).read_text(encoding="utf-8"))
        assert len(data.get("links", [])) > 0
        assert len(data.get("groups", [])) > 0


def test_main_workflow_has_correct_semantic_links():
    wf = json.loads(Path("workflows/99_main_one_shot_pipeline.json").read_text(encoding="utf-8"))
    by_id = {n["id"]: n["type"] for n in wf["nodes"]}

    def has_link(src_type, src_slot, dst_type, dst_slot):
        for l in wf["links"]:
            _, sid, sslot, tid, tslot, _ = l
            if by_id[sid] == src_type and sslot == src_slot and by_id[tid] == dst_type and tslot == dst_slot:
                return True
        return False

    assert has_link("FourK4D_InputIngest", 0, "FourK4D_ManifestGenerate", 0)
    assert has_link("FourK4D_ManifestGenerate", 0, "FourK4D_CommandBuilder", 2)
    assert has_link("FourK4D_ArtifactResolve", 0, "FourK4D_ArtifactDownload", 0)
    assert has_link("FourK4D_ArtifactDownload", 0, "FourK4D_CommandBuilder", 3)
    assert has_link("FourK4D_EnvBootstrap", 1, "FourK4D_EnvCheck", 1)
    assert has_link("FourK4D_EnvCheck", 0, "FourK4D_LaunchCommand", 3)
    assert has_link("FourK4D_Poll", 1, "FourK4D_ViewerLaunch", 6)


def test_workflow_nodes_have_explicit_io_metadata():
    for wf_dir in [Path("workflows"), Path("custom_nodes/ComfyUI_4K4D_Manager/workflows")]:
        for wf in wf_dir.glob("*.json"):
            data = json.loads(wf.read_text(encoding="utf-8"))
            by_id = {n["id"]: n for n in data["nodes"]}
            for n in data["nodes"]:
                assert "inputs" in n and "outputs" in n
            for lid, sid, sslot, tid, tslot, _ in data.get("links", []):
                assert by_id[sid]["outputs"][sslot]["links"] is not None
                assert lid in by_id[sid]["outputs"][sslot]["links"]
                assert by_id[tid]["inputs"][tslot]["link"] == lid


def test_artifact_download_skips_when_model_exists():
    with tempfile.TemporaryDirectory() as td:
        art = {"url": "https://example.com/never-used.ckpt", "target_relpath": "models/checkpoints/4k4d/4k4d_base.ckpt"}
        target = Path(td) / art["target_relpath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ready", encoding="utf-8")
        dl = FourK4DArtifactDownloadNode()
        path, log = dl.run(json.dumps(art), td, False)
        assert path == str(target)
        assert "already present" in log


def test_workflow_slots_have_slot_index_metadata():
    for wf_dir in [Path("workflows"), Path("custom_nodes/ComfyUI_4K4D_Manager/workflows")]:
        for wf in wf_dir.glob("*.json"):
            data = json.loads(wf.read_text(encoding="utf-8"))
            for n in data.get("nodes", []):
                for i, inp in enumerate(n.get("inputs", [])):
                    assert inp.get("slot_index") == i
                for i, out in enumerate(n.get("outputs", [])):
                    assert out.get("slot_index") == i
