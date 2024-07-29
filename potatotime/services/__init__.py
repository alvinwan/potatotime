from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime
from typing import List, Optional, Dict, ClassVar


class CalendarServiceInterface(ABC):
    event_serializer: 'EventSerializer'

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


class EventSerializer(ABC):
    @abstractmethod
    def serialize(self, field_name: str):
        pass

    @staticmethod
    @abstractmethod
    def deserialize(self, field_name: str, data: dict):
        pass


@dataclass
class BaseEvent:
    start: datetime
    end: datetime
    recurrence: Optional[List[str]]

    @classmethod
    def from_(cls, other: 'BaseEvent'):
        return cls(**{
            field.name: getattr(other, field.name)
            for field in fields(cls)
        })


@dataclass
class StubEvent(BaseEvent):
    """Used to serialize payloads for APIs"""
    def serialize(self, serializer: EventSerializer) -> dict:
        return {
            field.name: serializer.serialize(field.name, self)
            for field in fields(self)
        }


@dataclass
class CreatedEvent(BaseEvent):
    """Used to standardize event payloads returned by APIs"""
    id: str
    
    @classmethod
    def deserialize(cls, event_data: dict, serializer: EventSerializer):
        return cls(**{
            field.name: serializer.deserialize(field.name, event_data)
            for field in fields(cls)
        })


@dataclass
class ExtendedEvent(CreatedEvent):
    """Used to extract additional information from payloads returned by APIs"""
    declined: bool = False
    source_event_id: Optional[str] = None
