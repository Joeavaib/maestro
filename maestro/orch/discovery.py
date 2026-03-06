from __future__ import annotations
from pathlib import Path
from maestro.config import CommandCheck

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
