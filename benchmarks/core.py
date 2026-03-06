from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class BenchmarkInstance:
    instance_id: str
    repo: str
    problem_statement: str
    base_commit: str
    metadata: Dict[str, Any]

class BenchmarkAPI(ABC):
    """
    Abstract Base Class for all benchmark adapters.
    Ensures a consistent interface for loading data and evaluating results.
    """
    
    @abstractmethod
    def load_instances(self, subset: str = "public") -> List[BenchmarkInstance]:
        """Loads a list of benchmark instances from the source."""
        pass

    @abstractmethod
    def setup_environment(self, instance: BenchmarkInstance) -> Path:
        """Sets up the repository/container for a specific instance."""
        pass

    @abstractmethod
    def evaluate(self, instance: BenchmarkInstance, patch: str) -> Dict[str, Any]:
        """Runs the benchmark's evaluation suite against a generated patch."""
        pass
