from __future__ import annotations

import re
from dataclasses import dataclass

@dataclass
class Artifact:
    kind: str
    payload: str

def parse_artifact(output: str) -> Artifact:
    t = output.strip()
    
    # 1. Extract ALL fenced code blocks first (Ignore all conversational text outside!)
    blocks = re.findall(r"```(?:[a-zA-Z0-9_+-]+)?\n(.*?)\n```", t, re.DOTALL)
    
    if blocks:
        diff_payload = []
        file_payload = []
        
        for block in blocks:
            b = block.strip()
            if not b:
                continue
                
            # Is it a diff?
            if b.startswith("diff --git") or b.startswith("--- ") or b.startswith("@@ -"):
                diff_payload.append(b)
            else:
                # Does it have a FILE header inside the block?
                # Matches: FILE: path, // FILE: path, # File: path, etc.
                file_match = re.search(r"^(?:[+#/\[<* \t]*)(?:FILE|file|File)[\s:]+([^\n\s>\]]+)", b, re.IGNORECASE)
                
                if file_match:
                    path = file_match.group(1).strip()
                    # Strip the first line (the header) to get the clean code
                    content = b.split('\n', 1)[-1] if '\n' in b else ""
                    file_payload.append(f"FILE: {path}\n{content}")
                else:
                    # It's just generic code, give it a placeholder
                    file_payload.append(f"FILE: TARGET_FILE_PLACEHOLDER\n{b}")
        
        if diff_payload:
            return Artifact("diff", "\n\n".join(diff_payload))
        if file_payload:
            return Artifact("file_blocks", "\n\n".join(file_payload))

    # 2. Fallback (If the model completely forgot markdown fences)
    if t.startswith("diff --git") or t.startswith("--- ") or t.startswith("@@ -"):
        return Artifact("diff", t)

    # Search for FILE markers anywhere (Legacy fallback)
    file_match = re.search(r"(?:^|\n)(?:\+|-|#|\[|<)*\s*(?:FILE|file|File)[:\s]+([^\n\s]+)", t, re.IGNORECASE)
    if file_match:
        start_pos = file_match.start()
        sub = t[start_pos:].strip()
        sub = re.sub(r"^(?:\+|-|#|\[|<)*\s*(?:FILE|file|File)[:\s]*", "FILE: ", sub)
        sub = re.sub(r"<\s*/\s*(?:FILE|file|File)\s*>", "", sub)
        lines = sub.split("\n")
        lines[0] = re.sub(r"[\]>]", "", lines[0]).strip()
        return Artifact("file_blocks", "\n".join(lines))

    return Artifact("invalid", output)
