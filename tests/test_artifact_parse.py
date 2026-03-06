from maestro.orch.artifact import parse_artifact


def test_parse_artifact_accepts_plain_diff():
    out = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n"
    art = parse_artifact(out)
    assert art.kind == "diff"


def test_parse_artifact_extracts_diff_after_prose():
    out = "Here you go:\n\ndiff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n"
    art = parse_artifact(out)
    assert art.kind == "diff"
    assert art.payload.startswith("diff --git")


def test_parse_artifact_extracts_fenced_diff():
    out = "```diff\ndiff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n```"
    art = parse_artifact(out)
    assert art.kind == "diff"
    assert art.payload.startswith("diff --git")


def test_parse_artifact_extracts_file_blocks_after_prose():
    out = "Result:\nFILE: hello.txt\nhello\n"
    art = parse_artifact(out)
    assert art.kind == "file_blocks"
    assert art.payload.startswith("FILE: ")
