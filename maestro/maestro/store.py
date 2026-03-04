from __future__ import annotations

import json
import random
import shutil
import string
from pathlib import Path


def random_base36(n: int) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(n))


class RunStore:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()

    def init_run(self, sid: str | None = None, runid: str | None = None) -> dict[str, Path | str]:
        sid = sid or random_base36(random.randint(1, 16))
        runid = runid or random_base36(random.randint(1, 12))
        run_root = self.repo_path / "runs" / sid / runid
        work_repo = self.repo_path / ".maestro" / "work" / sid / runid / "repo"
        (run_root / "turns").mkdir(parents=True, exist_ok=True)
        work_repo.parent.mkdir(parents=True, exist_ok=True)
        return {"sid": sid, "runid": runid, "run_root": run_root, "work_repo": work_repo}

    def clone_repo_to_work(self, work_repo: Path) -> None:
        if work_repo.exists():
            shutil.rmtree(work_repo)
        shutil.copytree(self.repo_path, work_repo, ignore=shutil.ignore_patterns(".maestro", ".git"))
        
        import subprocess
        # Initialize a new git repo in the work directory for patch application
        subprocess.run(["git", "init"], cwd=work_repo, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=work_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial", "--quiet"], cwd=work_repo, capture_output=True)

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    @staticmethod
    def write_text(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload)
