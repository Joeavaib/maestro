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
    # Look for diff blocks anywhere, inside or outside fences
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
    # Matches "FILE: path/to/file\nCONTENT" or similar variants
    # Also handles variants like "# FILE: path", "// FILE: path", etc.
    file_blocks = []
    
    # First, look inside markdown fences for FILE markers
    fenced_blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", t, re.DOTALL)
    for block in fenced_blocks:
        b = block.strip()
        file_match = re.search(r"^(?:[+#/\[<* \t]*)(?:FILE|file|File)[\s:]+([^\n\s>\]]+)", b, re.IGNORECASE)
        if file_match:
            path = file_match.group(1).strip()
            content = b.split('\n', 1)[-1] if '\n' in b else ""
            file_blocks.append(f"FILE: {path}\n{content}")
        else:
            # If a fence is present but no FILE marker, we assume it's the target file
            file_blocks.append(f"FILE: TARGET_FILE_PLACEHOLDER\n{b}")

    if file_blocks:
        return Artifact("file_blocks", "\n\n".join(file_blocks), rationale)

    # Final fallback: Look for "FILE:" markers in the raw text
    raw_file_matches = re.finditer(r"(?:^|\n)(?:\+|-|#|\[|<)*\s*(?:FILE|file|File)[:\s]+([^\n\s>\]]+)", t, re.IGNORECASE)
    last_pos = -1
    last_path = None
    
    for match in raw_file_matches:
        if last_path:
            content = t[last_pos:match.start()].strip()
            file_blocks.append(f"FILE: {last_path}\n{content}")
        last_path = match.group(1).strip()
        last_pos = match.end()
        
    if last_path:
        content = t[last_pos:].split("</", 1)[0].strip() # Stop at XML closing tags
        file_blocks.append(f"FILE: {last_path}\n{content}")
        return Artifact("file_blocks", "\n\n".join(file_blocks), rationale)

    return Artifact("invalid", output, rationale)
