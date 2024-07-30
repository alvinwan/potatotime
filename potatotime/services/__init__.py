from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Optional
from potatotime.storage import Storage, FileStorage
import pytz


# TODO: new home for constants?
POTATOTIME_EVENT_SUBJECT = "Busy"
POTATOTIME_EVENT_DESCRIPTION = "Synchronized by PotatoTime 🥔"


class ServiceInterface(ABC):
    @abstractmethod
    def authorize(self, user_id: str, storage: Storage=FileStorage(), interactive: bool=True):
        """

        :param interactive: If true, will prompt user for authentication via a
            browser automatically. If not, throw an error when authentication
            fails.
        """
        pass


class CalendarInterface(ABC):
    event_serializer: 'EventSerializer'

    @abstractmethod
    def get_events(
        self,
        start: Optional[datetime]=None,
        end: Optional[datetime]=None,
        max_events: int=1000,
    ):
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
    is_all_day: bool

    @classmethod
    def from_(cls, other: 'BaseEvent'):
        return cls(**{
            field.name: getattr(other, field.name)
            for field in fields(cls)
        })
    
    def __eq__(self, other: 'BaseEvent'):
        for field in fields(self):
            self_value = getattr(self, field.name)
            other_value = getattr(other, field.name)
            if field.type is datetime:
                self_value = self_value.astimezone(pytz.utc)
                other_value = other_value.astimezone(pytz.utc)
            if self_value != other_value:
                return False
        return True


@dataclass
class StubEvent(BaseEvent):
    """Used to serialize payloads for APIs"""
    def serialize(self, serializer: EventSerializer) -> dict:
        payload = {}
        for field in fields(self):
            key, value = serializer.serialize(field.name, self)
            if key is not None:
                payload[key] = value
        return payload


@dataclass
class CreatedEvent(BaseEvent):
    """Used to standardize event payloads returned by APIs"""
    id: str
    url: str
    
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
