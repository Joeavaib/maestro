from __future__ import annotations

import re
from dataclasses import dataclass

@dataclass
class Artifact:
    kind: str
    payload: str
    rationale: str = ""

def parse_artifact(output: str) -> Artifact:
    """
    Surgically extracts code artifacts (Diffs or FILE blocks) from LLM responses.
    Handles markdown fences, XML tags, and conversational noise.
    """
    # 1. Extract Rationale (if present in XML tags)
    rationale_match = re.search(r"<rationale>(.*?)</rationale>", output, re.DOTALL | re.IGNORECASE)
    rationale = rationale_match.group(1).strip() if rationale_match else ""
    
    # Clean the output for easier parsing
    t = output.strip()
    
    # 2. Resilient Diff Search
    diff_patterns = [
        r"```(?:diff)?\n(diff --git.*?)\n```",
        r"```(?:diff)?\n(--- a/.*?)\n```",
        r"(diff --git .*?)(?=\n\n|\nFILE:|\n<|$)",
        r"(--- a/.*?)(?=\n\n|\nFILE:|\n<|$)"
    ]
    
    for pattern in diff_patterns:
        match = re.search(pattern, t, re.DOTALL)
        if match:
            return Artifact("diff", match.group(1).strip(), rationale)

    # 3. Resilient FILE Block Search
    # We prefer to return the WHOLE output if it contains "FILE:" markers, 
    # as apply_file_blocks is now smart enough to filter noise.
    if re.search(r"(?:^|\n)(?:\+|-|#|\[|<)*\s*(?:FILE|file|File)[:\s]+", t, re.IGNORECASE):
        # We clean common wrapping tags that might confuse the parser later
        clean_t = t
        if "<raw file content>" in clean_t:
            clean_t = clean_t.replace("<raw file content>", "").replace("</raw file content>", "")
        return Artifact("file_blocks", clean_t, rationale)

    # Fallback for single fenced blocks without FILE markers
    fenced_blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", t, re.DOTALL)
    if fenced_blocks:
        # If there's only one block, we assume it's the target file
        return Artifact("file_blocks", f"FILE: TARGET_FILE_PLACEHOLDER\n{fenced_blocks[0]}", rationale)

    return Artifact("invalid", output, rationale)
