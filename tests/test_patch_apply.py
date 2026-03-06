import subprocess
from pathlib import Path

from maestro.orch.patch import apply_diff


def _git(cmd, cwd: Path):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def test_reject_path_traversal(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(["git", "init"], repo)
    diff = "diff --git a/../x b/../x\n--- a/../x\n+++ b/../x\n@@ -0,0 +1 @@\n+oops\n"
    
    res = apply_diff(repo, diff)
    assert not res["ok"]


def test_apply_clean_diff(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(["git", "init"], repo)
    (repo / "a.txt").write_text("hello\n")
    _git(["git", "add", "."], repo)
    _git(["git", "commit", "-m", "init"], repo)
    diff = """diff --git a/a.txt b/a.txt
index ce01362..94954ab 100644
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-hello
+world
"""
    res = apply_diff(repo, diff)
    assert res["ok"]
    assert (repo / "a.txt").read_text() == "world\n"


def test_fail_cleanly_on_conflict(tmp_path: Path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(["git", "init"], repo)
    (repo / "a.txt").write_text("hello\n")
    _git(["git", "add", "."], repo)
    _git(["git", "commit", "-m", "init"], repo)
    diff = """diff --git a/a.txt b/a.txt
index ce01362..94954ab 100644
--- a/a.txt
+++ b/a.txt
@@ -1 +1 @@
-nope
+world
"""
    res = apply_diff(repo, diff)
    assert not res["ok"]
