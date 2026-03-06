from dataclasses import dataclass
from typing import Dict

@dataclass
class Event:
    type: str
    payload: Dict[str, any]

    def as_dict(self) -> Dict[str, any]:
        return {
            'type': self.type,
            'payload': self.payload
        }
