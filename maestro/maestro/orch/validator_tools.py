"""
Validator Tools für Repository-Analyse.
Alle Operationen sind read-only.
"""
from __future__ import annotations

import fnmatch
import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolResult:
    """Ergebnis eines Tool-Calls."""
    success: bool
    data: dict[str, Any]
    error: str | None = None


class ValidatorTools:
    """
    Sandbox-Tools für den Validator.
    
    Alle Pfade werden relativ zum work_repo interpretiert.
    Path Traversal wird blockiert.
    """
    
    def __init__(self, work_repo: Path, max_file_size: int = 100_000):
        self.work_repo = work_repo.resolve()
        self.max_file_size = max_file_size
        self._call_history: list[dict] = []
    
    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Führe ein Tool aus und logge es."""
        method_name = f"tool_{tool_name}"
        if not hasattr(self, method_name):
            return ToolResult(False, {}, error=f"Tool '{tool_name}' not found.")
        
        try:
            result_data = getattr(self, method_name)(**kwargs)
            res = ToolResult(True, result_data)
            self._call_history.append({
                "tool": tool_name,
                "args": kwargs,
                "success": True,
                "data": result_data
            })
            return res
        except Exception as e:
            err_msg = str(e)
            self._call_history.append({
                "tool": tool_name,
                "args": kwargs,
                "success": False,
                "error": err_msg
            })
            return ToolResult(False, {}, error=err_msg)
    
    def available_tools(self) -> list[str]:
        """Liste aller verfügbaren Tools."""
        return [
            name.replace("tool_", "") 
            for name in dir(self) 
            if name.startswith("tool_")
        ]
    
    def get_history(self) -> list[dict]:
        """History der Tool-Calls für den Validator-Context."""
        return self._call_history

    # --- Tool Implementations ---

    def tool_list_files(self, pattern: str = "**/*", max_results: int = 50) -> dict:
        """Listet Dateien im Repo."""
        files = []
        try:
            # Use glob to find files
            for p in self.work_repo.glob(pattern):
                if p.is_file() and not self._is_ignored(p):
                    files.append(str(p.relative_to(self.work_repo)))
                if len(files) >= max_results:
                    break
            
            return {
                "files": sorted(files),
                "count": len(files),
                "truncated": len(files) >= max_results
            }
        except Exception as e:
            raise ValueError(f"Error listing files with pattern '{pattern}': {e}")

    def tool_read_file(self, path: str, offset: int = 0, limit: int = 100) -> dict:
        """Liest Inhalt einer Datei."""
        safe_path = self._resolve_path(path)
        if not safe_path or not safe_path.exists():
            raise ValueError(f"File '{path}' not found or access denied.")
        
        if not safe_path.is_file():
            raise ValueError(f"Path '{path}' is not a file.")

        # Size check
        if safe_path.stat().st_size > self.max_file_size:
            raise ValueError(f"File '{path}' exceeds max size of {self.max_file_size} bytes.")

        try:
            content = safe_path.read_text(encoding='utf-8', errors='replace')
            lines = content.splitlines()
            total_lines = len(lines)
            
            sliced_lines = lines[offset:offset+limit]
            
            return {
                "path": path,
                "content": "\n".join(sliced_lines),
                "total_lines": total_lines,
                "shown_lines": len(sliced_lines),
                "offset": offset,
                "has_more": (offset + limit) < total_lines
            }
        except Exception as e:
            raise ValueError(f"Error reading file '{path}': {e}")

    def tool_grep_repo(self, query: str, file_pattern: str = "**/*", max_results: int = 20) -> dict:
        """Sucht nach Text im Repository."""
        matches = []
        try:
            for p in self.work_repo.glob(file_pattern):
                if p.is_file() and not self._is_ignored(p):
                    # Check size before reading for grep
                    if p.stat().st_size > self.max_file_size:
                        continue
                    
                    try:
                        content = p.read_text(encoding='utf-8', errors='replace')
                        for i, line in enumerate(content.splitlines()):
                            if query in line:
                                matches.append({
                                    "file": str(p.relative_to(self.work_repo)),
                                    "line": i + 1,
                                    "content": line.strip()[:200]
                                })
                                if len(matches) >= max_results:
                                    return {"matches": matches, "count": len(matches), "truncated": True}
                    except: continue
            
            return {"matches": matches, "count": len(matches), "truncated": False}
        except Exception as e:
            raise ValueError(f"Error grepping repo for '{query}': {e}")

    def tool_get_repo_structure(self, max_depth: int = 3) -> dict:
        """Zeigt Verzeichnisbaum."""
        def _build_tree(current_path: Path, depth: int) -> dict:
            if depth > max_depth:
                return {"name": current_path.name, "type": "dir", "truncated": True}
            
            children = []
            try:
                for p in sorted(current_path.iterdir()):
                    if self._is_ignored(p):
                        continue
                    
                    if p.is_dir():
                        children.append(_build_tree(p, depth + 1))
                    else:
                        children.append({"name": p.name, "type": "file"})
            except PermissionError:
                pass
                
            return {
                "name": current_path.name if current_path != self.work_repo else "repo",
                "type": "dir",
                "children": children
            }

        return {"structure": _build_tree(self.work_repo, 0)}

    def tool_check_symbol(self, symbol: str, language: str | None = None) -> dict:
        """Prüfe ob ein Symbol existiert."""
        patterns = {
            "py": [rf"def\s+{symbol}\s*\(", rf"class\s+{symbol}\s*[\(:]"],
            "js": [rf"function\s+{symbol}\s*\(", rf"class\s+{symbol}\s", rf"const\s+{symbol}\s*="],
            "ts": [rf"function\s+{symbol}\s*\(", rf"class\s+{symbol}\s", rf"const\s+{symbol}\s*=", rf"interface\s+{symbol}\s"],
            "rs": [rf"fn\s+{symbol}\s*\(", rf"struct\s+{symbol}\s", rf"enum\s+{symbol}\s"],
            "go": [rf"func\s+{symbol}\s*\(", rf"type\s+{symbol}\s+struct"]
        }
        
        relevant_extensions = {
            "py": "**/*.py",
            "js": "**/*.js",
            "ts": "**/*.ts",
            "rs": "**/*.rs",
            "go": "**/*.go"
        }

        # Filter by language or check all
        search_ext = relevant_extensions.get(language, "**/*") if language else "**/*"
        search_patterns = []
        if language and language in patterns:
            search_patterns = patterns[language]
        else:
            for p_list in patterns.values():
                search_patterns.extend(p_list)

        locations = []
        try:
            for p in self.work_repo.glob(search_ext):
                if p.is_file() and not self._is_ignored(p):
                    try:
                        content = p.read_text(encoding='utf-8', errors='replace')
                        for pattern in search_patterns:
                            if re.search(pattern, content):
                                locations.append({
                                    "file": str(p.relative_to(self.work_repo)),
                                    "type": "match"
                                })
                                break
                    except: continue
            
            return {
                "symbol": symbol,
                "found": len(locations) > 0,
                "locations": locations
            }
        except Exception as e:
            raise ValueError(f"Error checking symbol '{symbol}': {e}")

    # --- Helpers ---

    def _resolve_path(self, path: str) -> Path | None:
        """Resolve und validiere Pfad. Gibt None zurück bei Path Traversal."""
        try:
            # Join and resolve
            target = (self.work_repo / path).resolve()
            # Path Traversal Check: Muss innerhalb work_repo liegen
            if not str(target).startswith(str(self.work_repo)):
                return None
            return target
        except Exception:
            return None

    def _is_ignored(self, path: Path) -> bool:
        """Prüfe ob Datei ignoriert werden soll."""
        ignore_patterns = [
            ".git", "__pycache__", "*.pyc", ".maestro", 
            "node_modules", ".venv", "venv", ".pytest_cache"
        ]
        path_str = str(path)
        for pattern in ignore_patterns:
            if pattern in path_str or fnmatch.fnmatch(path.name, pattern):
                return True
        return False
