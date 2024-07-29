import caldav
from caldav.elements import dav, cdav
import pytz
import datetime
import os
from . import CalendarServiceInterface, EventSerializer, BaseEvent


class _AppleEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name == 'recurrence':
            return None # TODO: implement me
        if field_name in ('start', 'end'):
            return getattr(event, field_name)
        raise NotImplementedError(f"Serializing {field_name} is not supported")
    
    def deserialize(self, field_name: str, event_data):
        if field_name == 'id':
            return event_data.instance.vevent.uid.value
        if field_name in ('start', 'end'):
            return getattr(event_data.instance.vevent, f"dt{field_name}").value
        if field_name in ('url', 'recurrence', 'source_event_id'):
            return None  # TODO: implement me


class AppleCalendarService(CalendarServiceInterface):
    
    def __init__(self):
        self.client = caldav.DAVClient(
            url='https://caldav.icloud.com/',
            username=os.environ['POTATOTIME_APPLE_USERNAME'],
            password=os.environ['POTATOTIME_APPLE_PASSWORD'],
        )
        self.principal = self.client.principal()
        self.calendars = self.principal.calendars()
        self.event_serializer = _AppleEventSerializer()

    def authorize(self):
        # Authorization is handled in the constructor for Apple Calendar
        pass

    def _get_event(self, event_id):
        calendar = self.calendars[0]
        uid, start_time = event_id
        events = calendar.date_search(start=start_time, end=start_time + datetime.timedelta(hours=1))
        for event in events:
            if uid in event.data:
                return event
        print(f"No event found with UID: {event_id}")
        return None

    def create_event(self, event_data):
        calendar = self.calendars[0]  # Select the first calendar
        event = f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:{datetime.datetime.now().timestamp()}@example.com
DTSTART:{event_data['start'].strftime('%Y%m%dT%H%M%S')}
DTEND:{event_data['end'].strftime('%Y%m%dT%H%M%S')}
SUMMARY:{event_data.get('summary', '')}
DESCRIPTION:{event_data.get('description', '')}
LOCATION:{event_data.get('location', '')}
END:VEVENT
END:VCALENDAR
"""
        new_event = calendar.add_event(event)
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

    def get_events(self):
        calendar = self.calendars[0]
        now = datetime.datetime.utcnow()
        return calendar.date_search(start=now, end=now + datetime.timedelta(days=365))  # Fetch events for the next year
