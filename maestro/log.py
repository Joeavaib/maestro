from __future__ import annotations

from pathlib import Path
import json

class RunLogger:
    def __init__(self, run_root: Path):
        self.run_root = run_root

    def log_event(self, event_dict: dict):
        event_json = json.dumps(event_dict)
        with open(self.run_root / 'events.jsonl', 'a') as f:
            f.write(event_json + '\n')

class EventTracker(RunLogger):
    def __init__(self, run_root: Path):
        super().__init__(run_root)

    def append(self, event_dict: dict):
        event_json = json.dumps(event_dict)
        with open(self.run_root / 'events.jsonl', 'a') as f:
            f.write(event_json + '\n')

# Existing code remains unchanged
