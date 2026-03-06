class Event:
    def __init__(self, event_type: str, payload: dict):
        self.event_type = event_type
        self.payload = payload

    def as_dict(self) -> dict:
        return {
            'event_type': self.event_type,
            'payload': self.payload
        }
