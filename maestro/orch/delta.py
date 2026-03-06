from __future__ import annotations


def dotpath_to_relpath(dotpath: str) -> str:
    if not dotpath.startswith("f."):
        return dotpath
    body = dotpath[2:]
    parts = body.split(".")
    if len(parts) < 2:
        return body
    ext = parts[-1].replace("_", "")
    stem = parts[-2]
    dirs = parts[:-2]
    return "/".join(dirs + [f"{stem}.{ext}"])


def relpath_to_dotpath(relpath: str) -> str:
    relpath = relpath.strip("/")
    parts = relpath.split("/")
    last = parts[-1]
    if "." in last:
        stem, ext = last.rsplit(".", 1)
        parts = parts[:-1] + [stem, f"_{ext}"]
    return "f." + ".".join(parts)


def extract_delta(focus: str, last_artifact: str, checks_summary: str) -> str:
    if focus == "*":
        return f"last_artifact={last_artifact[:3000]}\nchecks={checks_summary}"
    return f"focus={focus}\nartifact={last_artifact[:3000]}"
