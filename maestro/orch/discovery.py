from __future__ import annotations
from pathlib import Path
from maestro.config import CommandCheck

def discover_repository_structure(repo_path: Path, max_depth: int = 3) -> str:
    """
    Generates a shallow directory tree to give Raven context about existing files.
    """
    import subprocess
    try:
        # Try using 'tree' if available for nice output
        res = subprocess.run(
            ["tree", "-L", str(max_depth), "--filelimit", "50", "-I", ".git|.maestro|node_modules|__pycache__|.pytest_cache|runs|dist|build"], 
            cwd=repo_path, capture_output=True, text=True
        )
        if res.returncode == 0:
            return res.stdout
    except FileNotFoundError:
        pass

    # Fallback to a simple find-based list
    try:
        res = subprocess.run(
            ["find", ".", "-maxdepth", str(max_depth), "-not", "-path", "*/.*", "-not", "-path", "./node_modules/*"], 
            cwd=repo_path, capture_output=True, text=True
        )
        if res.returncode == 0:
            return "\n".join(res.stdout.splitlines()[:100]) # Limit to first 100 entries
    except Exception:
        return "Could not discover repository structure."
    
    return "Repository structure unknown."

def discover_checks(repo_path: Path) -> list[CommandCheck]:
    """
    Scans the repository and suggests validation tools based on detected files.
    """
    checks = []
    
    # Rust
    if (repo_path / "Cargo.toml").exists():
        checks.append(CommandCheck(name="Cargo Check", cmd="cargo check", required=True))
        checks.append(CommandCheck(name="Clippy", cmd="cargo clippy -- -D warnings", required=True))
        checks.append(CommandCheck(name="Rust Format", cmd="cargo fmt --check", required=False))

    # Python
    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists() or list(repo_path.glob("*.py")):
        # Check for specific linters
        checks.append(CommandCheck(name="PyCompile", cmd="python3 -m py_compile **/*.py", required=True))
        if (repo_path / ".ruff.toml").exists() or (repo_path / "ruff.toml").exists():
             checks.append(CommandCheck(name="Ruff", cmd="ruff check .", required=True))

    # JavaScript / TypeScript
    if (repo_path / "package.json").exists():
        checks.append(CommandCheck(name="NPM Test", cmd="npm test", required=False))
        # Look for eslint
        if (repo_path / ".eslintrc.json").exists() or (repo_path / "eslint.config.js").exists():
             checks.append(CommandCheck(name="ESLint", cmd="npm run lint", required=True))

    return checks
