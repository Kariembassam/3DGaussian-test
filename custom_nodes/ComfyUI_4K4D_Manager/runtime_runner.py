import json
import os
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class JobState:
    job_id: str
    status: str
    pid: Optional[int]
    command: str
    workspace: str
    log_path: str
    started_at: float
    updated_at: float
    return_code: Optional[int] = None


class RuntimeJobRunner:
    def __init__(self, workspace: str):
        self.workspace = Path(workspace)
        self.jobs_dir = self.workspace / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.jobs_dir / "index.json"
        if not self.index_path.exists():
            self._save_index({})

    def _load_index(self) -> Dict[str, dict]:
        if not self.index_path.exists():
            return {}
        with self.index_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, data: Dict[str, dict]) -> None:
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _is_running(self, pid: Optional[int]) -> bool:
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def launch(self, command: str, cwd: str, env: Optional[dict] = None) -> JobState:
        job_id = str(uuid.uuid4())
        log_path = self.jobs_dir / f"{job_id}.log"
        log_file = log_path.open("w", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid,
        )
        now = time.time()
        state = JobState(
            job_id=job_id,
            status="running",
            pid=process.pid,
            command=command,
            workspace=str(self.workspace),
            log_path=str(log_path),
            started_at=now,
            updated_at=now,
        )
        index = self._load_index()
        index[job_id] = state.__dict__
        self._save_index(index)
        return state

    def poll(self, job_id: str) -> JobState:
        index = self._load_index()
        if job_id not in index:
            raise ValueError(f"Unknown job_id: {job_id}")
        state = JobState(**index[job_id])
        running = self._is_running(state.pid)
        state.updated_at = time.time()
        if not running and state.status == "running":
            state.status = "finished"
            state.return_code = self._get_return_code_from_log(state.log_path)
        index[job_id] = state.__dict__
        self._save_index(index)
        return state

    def stop(self, job_id: str) -> JobState:
        index = self._load_index()
        if job_id not in index:
            raise ValueError(f"Unknown job_id: {job_id}")
        state = JobState(**index[job_id])
        if state.pid and self._is_running(state.pid):
            os.killpg(state.pid, signal.SIGTERM)
            state.status = "stopped"
            state.return_code = -15
        state.updated_at = time.time()
        index[job_id] = state.__dict__
        self._save_index(index)
        return state

    def _get_return_code_from_log(self, log_path: str) -> Optional[int]:
        # Return code recovery isn't robust post-detach; preserve unknown.
        return None
