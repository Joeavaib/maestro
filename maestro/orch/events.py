class Event:
    def __init__(self, type: str, payload: dict):
        self.type = type
        self.payload = payload

    def as_dict(self) -> dict:
        return {
            'type': self.type,
            'payload': self.payload
        }
