from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict


class CalendarServiceInterface(ABC):
    @abstractmethod
    def authorize(self):
        pass

    @abstractmethod
    def get_events(self):
        pass

    @abstractmethod
    def create_event(self, event_data):
        pass

    @abstractmethod
    def update_event(self, event_id, update_data):
        pass

    @abstractmethod
    def delete_event(self, event_id):
        pass


@dataclass
class CalendarEvent:
    start: datetime
    end: datetime
    id: Optional[str] = None
    url: Optional[str] = None
    recurrence: Optional[List[str]] = None
    is_copy: bool = False

    @abstractmethod
    def serialize(self) -> dict:
        pass

    @staticmethod
    @abstractmethod
    def deserialize(event_data: dict):
        pass

    @classmethod
    def from_(cls, event: 'CalendarEvent'):
        return cls(
            start=event.start,
            end=event.end,
            id=event.id,
            url=event.url,
            recurrence=event.recurrence,
            is_copy=event.is_copy,
        )