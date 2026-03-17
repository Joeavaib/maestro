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


import re

def apply_file_blocks(repo: Path, payload: str) -> dict:
    """
    Applies raw file blocks (FILE: path\ncontent).
    Surgically ignores conversational noise before the first block.
    """
    import os
    blocks: list[tuple[str, list[str]]] = []
    current_path = None
    current_buf = []

    for line in payload.splitlines():
        # Case-insensitive "FILE: path" match, also handles common comment variants
        file_match = re.match(r"^(?:[+#/\[<* \t]*)(?:FILE|file|File)[\s:]+([^\n\s>\]]+)", line, re.IGNORECASE)
        if file_match:
            if current_path:
                blocks.append((current_path, current_buf))
            current_path = file_match.group(1).strip()
            current_buf = []
        elif current_path:
            current_buf.append(line)

    if current_path:
        blocks.append((current_path, current_buf))

    if not blocks:
        return {"ok": False, "error": "No valid FILE blocks found in the output."}

    repo_str = str(repo.resolve())

    for path, buf in blocks:
        # Strip absolute repo path prefix if the model hallucinates it
        if path.startswith(repo_str):
            path = path[len(repo_str):].lstrip("/\\")
        
        # Sanitize path
        target = (repo / path).resolve()
        if repo.resolve() not in target.parents and target != repo.resolve():
            return {"ok": False, "error": f"Path traversal detected: {path}"}

        # Surgical cleaning of the buffer
        clean_buf = []
        for i, line in enumerate(buf):
            # Strip markdown fences and wrapping tags if they appear at start/end of content
            stripped = line.strip()
            if stripped.startswith("```") or stripped.endswith("```"):
                continue
            if stripped in ["<raw file content>", "</raw file content>", "</rationale>"]:
                continue
            clean_buf.append(line)

        # Final trimming of leading/trailing whitespace in the file content
        content = "\n".join(clean_buf).strip() + "\n"
        
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except Exception as e:
            return {"ok": False, "error": f"Failed to write to {path}: {str(e)}"}

    return {"ok": True}
