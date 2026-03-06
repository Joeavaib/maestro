from __future__ import annotations

import subprocess
import time
from pathlib import Path

from maestro.config import RunnerConfig


def run_checks(repo: Path, cfg: RunnerConfig, patch_applied: bool) -> dict:
    commands = []
    all_ok = True
    for chk in cfg.checks:
        start = time.time()
        p = subprocess.run(chk.cmd, shell=True, cwd=repo / chk.cwd, capture_output=True, text=True, timeout=chk.timeout_s)
        duration_ms = int((time.time() - start) * 1000)
        ok = p.returncode == 0
        if chk.required and not ok:
            all_ok = False
        commands.append(
            {
                "name": chk.name,
                "exit_code": p.returncode,
                "duration_ms": duration_ms,
                "stdout_tail": p.stdout[-400:],
                "stderr_tail": p.stderr[-400:],
            }
        )
    return {
        "patch_applied": patch_applied,
        "format_ok": all_ok if commands else None,
        "lint_ok": all_ok if commands else None,
        "tests_ok": all_ok if commands else None,
        "summary": "ok" if all_ok and patch_applied else "failed",
        "commands": commands,
    }
