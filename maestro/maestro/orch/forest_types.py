from __future__ import annotations

import subprocess
import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TreeTask:
    id: str
    description: str
    intent: str
    keywords: str
    target_files: str
    tools: List[str] = field(default_factory=list)
    validation_command: Optional[str] = None
    complexity: int = 2  # 1=Trivial, 2=Normal, 3=Complex, 4=Expert

@dataclass
class ForestPlan:
    goal: str
    tasks: List[TreeTask]

class CXMBridge:
    """
    Bridge to the external 'cxm' CLI tool for context harvesting.
    """
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def harvest(self, keywords: str, intent: str) -> str:
        """
        Calls 'cxm harvest' to get the perfect context for the Tree.
        """
        # Wir bereiten den Call vor. Falls CXM noch nicht den 'harvest' Befehl
        # hat, nutzen wir einen Fallback oder rufen es entsprechend auf.
        try:
            # We assume cxm is available in the environment/PATH
            cmd = [
                "cxm", "harvest", 
                keywords, 
                "--intent", intent, 
                "--format", "xml"
            ]
            print(f"[CXM] Harvesting context with: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"[CXM] Warning: Harvest failed ({result.returncode}). Stderr: {result.stderr}")
                return f"<!-- CXM Harvest Failed: {result.stderr} -->"
        except FileNotFoundError:
            print("[CXM] 'cxm' executable not found. Ensure it is installed and in PATH.")
            return "<!-- CXM tool not available. No context harvested. -->"
        except subprocess.TimeoutExpired:
            print("[CXM] Timeout while harvesting context.")
            return "<!-- CXM Harvest Timeout -->"
