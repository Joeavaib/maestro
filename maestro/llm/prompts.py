from __future__ import annotations

VALIDATOR_SYSTEM_PROMPT = """You are the TMP-S Lite Validator. Output ONLY Lite records, no prose.

### FORMAT:
A ok|score|rationale
E location|fix (optional, max 3)
B agent|action (optional, max 3)
C decision|focus (optional)

### FIELDS:
- ok: 0 (Fail) or 1 (Pass/Warn)
- score: 0-9 (Quality score)
- rationale: Brief explanation
- decision: A (Accept), R (Reject/Retry), E (Escalate)
- focus: file path or *

### CRITICAL RULES:
1. ONLY lines starting with A, E, B, or C are allowed.
2. If request is fulfilled and checks are 'ok' -> A 1|9|... C A|*
3. If error exists -> A 0|score|... E file|fix ... B agent|task ... C R|file
4. Turn 0 must always be C R|* or C R|file.
"""

VALIDATOR_SYSTEM_PROMPT_WITH_TOOLS = """You are the TMP-S Lite Validator with REPO TOOLS.

### OUTPUT OPTIONS:
You have TWO possible output formats:

1. TOOL CALL (when you need to inspect the repo):
   TOOL:tool_name|arg1=value1|arg2=value2
   
   Available tools:
   - list_files(pattern='**/*.py', max_results=50)
   - read_file(path='src/main.py', offset=0, limit=100)
   - grep_repo(query='class ', file_pattern='*.py', max_results=20)
   - get_repo_structure(max_depth=3)
   - check_symbol(symbol='MyClass', language='py')

2. TMP-S LITE RECORD (final decision):
   A ok|score|rationale
   E location|fix (optional, max 3)
   B agent|action (optional, max 3)
   C decision|focus (optional)

### DECISION FLOW:
1. Analyze the current state from [PATCH_APPLY] and [CHECKS]
2. IF you need to verify something in the repo -> Output TOOL call.
3. WHEN you have enough information -> Output final Lite record.

### CRITICAL RULES:
1. Use tools BEFORE making final decision if unsure.
2. Max 3 tool calls per turn.
3. Output EXACT Lite format for final decision.
"""

# Specialist prompts - NO TMP-S, human readable only!

def build_specialist_prompt(
    strategy: int, 
    agent: str, 
    request: str, 
    validator_feedback: str, 
    delta: str, 
    task: str
) -> str:
    """
    Build a prompt for specialist agents.
    Optimized for small models (3B-8B) to ensure valid git diffs.
    """
    
    header = (
        f"### YOU ARE A {agent.upper()} SPECIALIST ###\n"
        f"STRICT TASK: {task}\n\n"
        f"USER REQUEST: {request[:500]}\n"
        f"VALIDATOR FEEDBACK: {validator_feedback}\n"
        f"CURRENT CODE/CONTEXT:\n{delta}\n\n"
    )

    instructions = (
        "### OUTPUT FORMAT RULES (CRITICAL) ###\n"
        "1. NO PROSE. NO EXPLANATIONS. NO MARKDOWN BLOCKS (```).\n"
        "2. FOR CHANGES: Output ONLY a UNIFIED DIFF.\n"
        "   - MUST start with: --- a/path/to/file\n"
        "   - MUST follow with: +++ b/path/to/file\n"
        "3. FOR NEW FILES: Output ONLY a FILE block.\n"
        "   - Format: FILE: path/to/file\\n<CONTENT>\n\n"
        "### EXAMPLE OF VALID DIFF (FOLLOW THIS EXACTLY): ###\n"
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -1,3 +1,4 @@\n"
        " def main():\n"
        "+    \"\"\"This is a docstring.\"\"\"\n"
        "     print('Hello')\n\n"
        "### START YOUR RESPONSE WITH --- OR FILE: ###"
    )
    
    return header + instructions


def build_validator_feedback(
    verdict: str,
    rationale: str,
    errors: list[str],
    patch_applied: bool,
    checks_summary: str
) -> str:
    """
    Convert TMPS validator output to human-readable feedback for specialists.
    
    Args:
        verdict: P (Pass), W (Warning), F (Fail), H (Hard Fail)
        rationale: Short description of the issue
        errors: List of specific errors found
        patch_applied: Whether the patch was successfully applied
        checks_summary: Summary of check results
    
    Returns:
        Human-readable feedback string
    """
    verdict_map = {
        "P": "✓ PASSED - Changes look good",
        "W": "⚠ WARNING - Minor issues, can proceed",
        "F": "✗ FAILED - Needs revision",
        "H": "✗ HARD FAIL - Major issues detected"
    }
    
    feedback_lines = [
        f"Status: {verdict_map.get(verdict, verdict)}",
        f"Issue: {rationale}",
    ]
    
    if not patch_applied:
        feedback_lines.append("CRITICAL: Patch could not be applied - likely syntax error or wrong line numbers")
    
    if checks_summary and checks_summary != "passed":
        feedback_lines.append(f"Checks: {checks_summary}")
    
    if errors:
        feedback_lines.append("Specific errors:")
        for err in errors[:5]:  # Limit to 5 errors
            feedback_lines.append(f"  - {err}")
    
    return "\n".join(feedback_lines)
