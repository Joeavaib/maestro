from __future__ import annotations

from pathlib import Path


class RunLogger:
    def __init__(self, run_root: Path):
        self.run_root = run_root

    def turn_dir(self, turn: int) -> Path:
        path = self.run_root / "turns" / str(turn)
        path.mkdir(parents=True, exist_ok=True)
        return path
