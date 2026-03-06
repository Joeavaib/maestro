from pathlib import Path
import json

class RunLogger:
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.log_file = run_root / "log.txt"
        self.log_file.touch(exist_ok=True)

    def log(self, message: str) -> None:
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")

class EventTracker:
    def __init__(self, run_root: Path):
        self.run_root = run_root
        self.events_file = run_root / "events.jsonl"
        self.events_file.touch(exist_ok=True)

    def append(self, event_dict: dict) -> None:
        with open(self.events_file, 'a') as f:
            json.dump(event_dict, f)
            f.write("\n")
