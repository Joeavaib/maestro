from dataclasses import dataclass

@dataclass
class Event:
    type: str
    payload: dict

    def as_dict(self) -> dict:
        return {
            "type": self.type,
            "payload": self.payload
        }
