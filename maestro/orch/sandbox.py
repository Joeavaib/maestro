from __future__ import annotations

import shutil
from pathlib import Path


def prepare_sandbox(src_repo: Path, sandbox_repo: Path) -> None:
    if sandbox_repo.exists():
        shutil.rmtree(sandbox_repo)
    shutil.copytree(src_repo, sandbox_repo, ignore=shutil.ignore_patterns(".maestro", ".git"))
