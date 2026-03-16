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
    # ... (existing RunStore code remains)
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

class ShadowStore:
    """
    Manages the 'Shadow Git' layer of Maestro.
    This layer sits between the user's real repository and the AI's work sandbox.
    It maintains 'maestro-stable' and 'maestro-experimental' branches.
    """
    def __init__(self, main_repo_path: Path):
        self.main_repo_path = main_repo_path.resolve()
        self.shadow_root = self.main_repo_path / ".maestro" / "shadow"

    def initialize_shadow(self) -> Path:
        """
        Creates a clean shadow clone of the project and sets up Maestro branches.
        Returns the path to the shadow repository.
        """
        import subprocess
        if not self.shadow_root.exists():
            self.shadow_root.mkdir(parents=True, exist_ok=True)

        # Use the folder name as project ID for the shadow repo
        project_name = self.main_repo_path.name
        shadow_repo = self.shadow_root / project_name

        if shadow_repo.exists():
            print(f"[*] Shadow repo already exists at {shadow_repo}")
            return shadow_repo

        print(f"[*] Creating new Shadow Repository for project: {project_name}")
        
        # 1. Copy current state (excluding Maestro's own internal folders)
        shutil.copytree(
            self.main_repo_path, 
            shadow_repo, 
            ignore=shutil.ignore_patterns(".maestro", ".git", "runs", "__pycache__", "node_modules")
        )

        # 2. Initialize Git in Shadow
        subprocess.run(["git", "init"], cwd=shadow_repo, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=shadow_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Maestro: Initial Import", "--quiet"], cwd=shadow_repo, capture_output=True)

        # 3. Setup Branches
        # Rename current branch to 'maestro-stable'
        subprocess.run(["git", "branch", "-m", "maestro-stable"], cwd=shadow_repo, capture_output=True)
        # Create 'maestro-experimental' from stable
        subprocess.run(["git", "checkout", "-b", "maestro-experimental"], cwd=shadow_repo, capture_output=True)

        print(f"[✅] Shadow Git initialized with branches: maestro-stable, maestro-experimental")
        return shadow_repo

    def get_experimental_path(self) -> Path:
        """Returns the path to the shadow repo, ensuring it is on the experimental branch."""
        project_name = self.main_repo_path.name
        shadow_repo = self.shadow_root / project_name
        return shadow_repo


    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))

    @staticmethod
    def write_text(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload)
