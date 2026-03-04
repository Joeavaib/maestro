from __future__ import annotations

import subprocess
from pathlib import Path


def _reject_unsafe_diff(diff: str, allow_renames: bool = False) -> str | None:
    for line in diff.splitlines():
        if line.startswith("Binary files"):
            return "binary diff rejected"
        if line.startswith("rename ") and not allow_renames:
            return "rename rejected"
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            path = line[6:]
            if ".." in path.split("/"):
                return "path traversal"
    return None


def apply_diff(repo: Path, diff: str, allow_renames: bool = False, focus: str = None) -> dict:
    # If header is missing but we have a hunk start and a focus file, prepend synthetic header
    if diff.startswith("@@ -") and focus and focus != "*" and "," not in focus:
        header = f"--- a/{focus}\n+++ b/{focus}\n"
        diff = header + diff

    reason = _reject_unsafe_diff(diff, allow_renames)
    if reason:
        return {"ok": False, "error": reason}
    p = subprocess.run(["git", "apply", "--check", "-"], input=diff, text=True, cwd=repo, capture_output=True)
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.strip() or "apply check failed"}
    p2 = subprocess.run(["git", "apply", "-"], input=diff, text=True, cwd=repo, capture_output=True)
    if p2.returncode != 0:
        return {"ok": False, "error": p2.stderr.strip() or "apply failed"}
    return {"ok": True}


def apply_file_blocks(repo: Path, payload: str) -> dict:
    current = None
    buf: list[str] = []
    def flush() -> str | None:
        nonlocal current, buf
        if current is None:
            return None
        target = (repo / current).resolve()
        if repo.resolve() not in target.parents and target != repo.resolve():
            return "path traversal"
        target.parent.mkdir(parents=True, exist_ok=True)

        # Strip markdown fences if present
        clean_buf = []
        in_fence = False
        for i, line in enumerate(buf):
            if line.startswith("```"):
                continue
            clean_buf.append(line)

        target.write_text("\n".join(clean_buf).rstrip("\n") + "\n")
        return None

    for line in payload.splitlines():
        if line.startswith("FILE: "):
            err = flush()
            if err:
                return {"ok": False, "error": err}
            current = line[6:].strip()
            buf = []
        else:
            buf.append(line)
    err = flush()
    if err:
        return {"ok": False, "error": err}
    return {"ok": current is not None}
