from __future__ import annotations

import json
from pathlib import Path


def build_validator_input(
    mode: str,
    request: str,
    repo_summary: str,
    artifact_kind: str,
    artifact: str,
    patch_apply: dict,
    checks: dict,
    last_tmps: str,
    cap: int,
    history: str = "",
    tool_history: list[dict] | None = None,
    *,
    sid: str,
    runid: str,
    turn: int,
    budget_after_turn: int,
) -> str:
    payload_parts = [
        f"[SID] {sid}",
        f"[RUNID] {runid}",
        f"[TURN] {turn}",
        f"[BUDGET_AFTER_TURN] {budget_after_turn}",
        f"[MODE] {mode}",
        f"[REQUEST] {request}",
        f"[REPO_SUMMARY] {repo_summary}",
        f"[ARTIFACT_KIND] {artifact_kind}",
        f"[ARTIFACT] {artifact[:8000]}",
        f"[PATCH_APPLY] {json.dumps(patch_apply, sort_keys=True)}",
        f"[CHECKS] {json.dumps(checks, sort_keys=True)}",
        f"[LAST_TMPS] {last_tmps if last_tmps else 'NONE'}",
    ]

    if tool_history:
        payload_parts.append("\n[TOOL_HISTORY]")
        for call in tool_history:
            status = "SUCCESS" if call.get("success") else "FAILED"
            payload_parts.append(f"  {call['tool']}({call['args']}) -> {status}")
            if not call.get("success"):
                payload_parts.append(f"    Error: {call.get('error')}")

    payload_parts.append(f"\n[HISTORY]\n{history}")
    
    payload = "\n".join(payload_parts)
    return payload[:cap]


def parse_tool_call(text: str) -> tuple[str, dict] | None:
    """
    Parse einen Tool-Call aus Validator Output.
    Format: TOOL:tool_name|arg1=value1|arg2=value2
    """
    text = text.strip()
    if not text.startswith("TOOL:"):
        return None
    
    parts = text[5:].split("|")
    if not parts or not parts[0]:
        return None
    
    tool_name = parts[0].strip()
    kwargs = {}
    for part in parts[1:]:
        if "=" not in part: continue
        k, v = part.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Type conversion
        if v.isdigit(): v = int(v)
        elif v.lower() == "true": v = True
        elif v.lower() == "false": v = False
        kwargs[k] = v
    return tool_name, kwargs


def get_repo_context(work_repo: Path, focus: str, max_lines: int = 50) -> str:
    """
    Extract relevant code context from the repository for specialists.
    
    Args:
        work_repo: Path to the working repository
        focus: File path or dotpath (e.g., "index.html" or "src/main.js:15")
        max_lines: Maximum lines to include
    
    Returns:
        String with file content or error message
    """
    # Parse focus to get file path
    if ":" in focus:
        file_path = focus.split(":")[0]
    else:
        file_path = focus
    
    if file_path == "*" or not file_path:
        # No specific focus, return summary of all files
        return _get_repo_summary(work_repo)
    
    target_file = work_repo / file_path
    
    if not target_file.exists():
        # File doesn't exist yet - might be a new file
        return f"# File {file_path} does not exist yet (will be created)\n"
    
    try:
        content = target_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        if len(lines) > max_lines:
            # If file is too large, show beginning and indicate truncation
            shown = '\n'.join(lines[:max_lines])
            return f"# {file_path} (first {max_lines} lines of {len(lines)}):\n```\n{shown}\n# ... ({len(lines) - max_lines} more lines)\n```\n"
        else:
            return f"# {file_path}:\n```\n{content}\n```\n"
    
    except Exception as e:
        return f"# Error reading {file_path}: {e}\n"


def _get_repo_summary(work_repo: Path) -> str:
    """Get a summary of files in the repository."""
    try:
        files = list(work_repo.iterdir())
        file_list = [f.name for f in files if f.is_file()]
        return f"# Repository files: {', '.join(file_list)}\n"
    except Exception:
        return "# Repository (unknown structure)\n"


def build_specialist_context(
    work_repo: Path,
    request: str,
    validator_feedback: str,
    focus: str,
    delta: str,
    task: str,
    agent: str = "bld",
) -> str:
    """
    Build complete context for specialist agents including repo content.
    
    This ensures specialists see the ACTUAL code, not hallucinated content.
    """
    context_parts = [
        f"You are a {agent} specialist. Your task: {task}\n",
        f"## ORIGINAL REQUEST\n{request}\n",
        f"## FEEDBACK FROM VALIDATOR\n{validator_feedback}\n",
    ]
    
    # Add repo context - THE IMPORTANT PART!
    if focus and focus != "*":
        repo_ctx = get_repo_context(work_repo, focus)
        context_parts.append(f"## CURRENT CODE CONTEXT\n{repo_ctx}")
    
    if delta:
        context_parts.append(f"## CHANGES NEEDED\n{delta}\n")
    
    context_parts.append(
        "## INSTRUCTIONS\n"
        "- Read the CURRENT CODE CONTEXT above carefully\n"
        "- Output ONLY unified diff or FILE blocks\n"
        "- NO explanations, NO markdown code fences\n"
        "- Diff must apply cleanly to the CURRENT CODE\n"
        "- If creating a NEW file, use FILE: path/to/file\n"
    )
    
    return "\n".join(context_parts)
