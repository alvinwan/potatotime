from abc import ABC, abstractmethod


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
