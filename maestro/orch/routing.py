from __future__ import annotations


def route_initial_agent(request: str) -> str:
    lower = request.lower()
    if any(x in lower for x in ["failing tests", "traceback", "crash"]):
        return "dbg"
    if any(x in lower for x in ["security", "auth", "crypto", "injection"]):
        return "sec"
    if any(x in lower for x in ["docs", "readme", "documentation"]):
        return "doc"
    if any(x in lower for x in ["implement", "feature", "add endpoint", "build"]):
        return "imp"
    return "imp"
