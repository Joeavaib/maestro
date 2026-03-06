from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Artifact:
    kind: str
    payload: str


def _extract_fenced_block(output: str) -> str | None:
    for pattern in (
        r"```(?:diff)?\s*\n(.*?)\n```",
        r"```\s*\n(.*?)\n```",
    ):
        m = re.search(pattern, output, flags=re.DOTALL)
        if m:
            return m.group(1).strip("\n")
    return None


def parse_artifact(output: str) -> Artifact:
    t = output.lstrip()
    
    # 1. Try to find the block (either raw or fenced)
    fenced = _extract_fenced_block(t)
    payload = fenced if fenced else t
    
    # 2. Identify kind (diff or file_blocks)
    if payload.startswith("diff --git") or payload.startswith("--- ") or payload.startswith("@@ -"):
        return Artifact("diff", payload)
    if payload.startswith("FILE: ") or payload.startswith("+FILE: ") or payload.startswith("+# File: "):
        # Normalize to FILE:
        norm_payload = payload
        if norm_payload.startswith("+"): norm_payload = norm_payload[1:]
        if norm_payload.startswith("# File: "): norm_payload = "FILE: " + norm_payload[8:]
        return Artifact("file_blocks", norm_payload)

    # 3. Fallback: Search anywhere in the text
    diff_idx = t.find("diff --git")
    if diff_idx < 0:
        diff_idx = t.find("--- ")
    if diff_idx < 0:
        diff_idx = t.find("@@ -")
        
    if diff_idx >= 0:
        raw_payload = t[diff_idx:]
        # Remove trailing markdown fence if present
        if "```" in raw_payload:
            raw_payload = raw_payload.split("```")[0].strip()
        return Artifact("diff", raw_payload)

    file_idx = t.find("FILE: ")
    if file_idx < 0: file_idx = t.find("+FILE: ")
    if file_idx < 0: file_idx = t.find("+# File: ")
        
    if file_idx >= 0:
        # Normalize the substring
        sub = t[file_idx:]
        if sub.startswith("+"): sub = sub[1:]
        if sub.startswith("# File: "): sub = "FILE: " + sub[8:]
        return Artifact("file_blocks", sub)

    return Artifact("invalid", output)
