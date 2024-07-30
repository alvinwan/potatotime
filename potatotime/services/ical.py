import caldav
import datetime
import os
from typing import Optional, List, Dict
from . import ServiceInterface, CalendarInterface, EventSerializer, BaseEvent, POTATOTIME_EVENT_SUBJECT, POTATOTIME_EVENT_DESCRIPTION
from potatotime.storage import Storage, FileStorage


class _AppleEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name in ('is_all_day',):
            return None, None # TODO: implement me
        if field_name in ('start', 'end'):
            return field_name, getattr(event, field_name)
        raise NotImplementedError(f"Serializing {field_name} is not supported")
    
    def deserialize(self, field_name: str, event_data):
        if field_name == 'id':
            return event_data.instance.vevent.uid.value
        if field_name in ('start', 'end'):
            return getattr(event_data.instance.vevent, f"dt{field_name}").value
        if field_name in ('url', 'source_event_id', 'declined'):
            return None  # TODO: implement me


class AppleService(ServiceInterface):
    
    def __init__(self):
        self.client = caldav.DAVClient(
            url='https://caldav.icloud.com/',
            username=os.environ['POTATOTIME_APPLE_USERNAME'],
            password=os.environ['POTATOTIME_APPLE_PASSWORD'],
        )
        self.principal = self.client.principal()
        self.calendars = self.principal.calendars()
        self.event_serializer = _AppleEventSerializer()

    def authorize(self, user_id: str, storage: Storage=FileStorage(), interactive: bool=True):
        # Authorization is handled in the constructor for Apple Calendar
        pass

    def list_calendars(self) -> List[Dict]:
        return [{'id': cal.url, 'name': cal.name, 'object': cal} for cal in self.calendars]

    # TODO: duplicated from GoogleCalendar
    def get_calendar(self, calendar_id: Optional[str]=None):
        calendars = self.list_calendars()
        for calendar in calendars:
            if calendar['id'] == calendar_id or calendar_id is None:
                return AppleCalendar(self, calendar['object'])
        raise ValueError(f'Invalid calendar_id: {calendar_id}')


class AppleCalendar(CalendarInterface):

    def __init__(self, service, calendar):
        self.service = service
        self.calendar = calendar
        self.event_serializer = _AppleEventSerializer()

    def create_event(self, event_data):
        event = f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:{datetime.datetime.now().timestamp()}@example.com
DTSTART:{event_data['start'].strftime('%Y%m%dT%H%M%S')}
DTEND:{event_data['end'].strftime('%Y%m%dT%H%M%S')}
SUMMARY:{POTATOTIME_EVENT_SUBJECT}
DESCRIPTION:{POTATOTIME_EVENT_DESCRIPTION}
LOCATION:{event_data.get('location', '')}
END:VEVENT
END:VCALENDAR
"""
        new_event = self.calendar.add_event(event)
        print(f"Event '{new_event.instance.vevent.uid.value}' created with UID: {new_event.instance.vevent.uid.value}")
        return new_event

    def update_event(self, event, update_data):
        if event:
            component = event.vobject_instance.vevent
            if 'start' in update_data:
                component.dtstart.value = update_data['start']
            if 'end' in update_data:
                component.dtend.value = update_data['end']
            if 'summary' in update_data:
                component.summary.value = update_data['summary']
            if 'description' in update_data:
                component.description.value = update_data['description']
            if 'location' in update_data:
                component.location.value = update_data['location']
            event.save()
            print(f"Event '{event.vobject_instance.vevent.uid.value}' edited.")

    def delete_event(self, event):
        event.delete()
        print(f'Event "{event.instance.vevent.uid.value}" deleted')

    def get_events(
        self,
        start: Optional[datetime.datetime]=None,
        end: Optional[datetime.datetime]=None,
        max_events: int=1000,
    ):  
        if not start:
            start = datetime.datetime.utcnow()
        if not end:
            end = start + datetime.timedelta(days=30)
        
        all_events = []
        events = self.calendar.date_search(start=start, end=end)
        
        for event in events:
            all_events.append(event)
            if len(all_events) >= max_events:
                return all_events[:max_events]

        return all_events