import caldav
from caldav.elements import dav, cdav
import pytz
from datetime import datetime, timedelta
import os

# Connect to iCloud calendar
client = caldav.DAVClient(
    url='https://caldav.icloud.com/',
    username=os.environ['POTATOTIME_APPLE_USERNAME'],
    password=os.environ['POTATOTIME_APPLE_PASSWORD'],
)

# Fetch principal
principal = client.principal()

# List all calendars
calendars = principal.calendars()

# Fetch events from each calendar
for calendar in calendars:
    print(f"Fetching events from calendar: {calendar.name}")
    events = calendar.date_search(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now() + timedelta(days=30)
    )
    
    for event in events:
        print(event.data)

def create_event(calendar, start_time, end_time, summary, description, location):
    event = f"""
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:{datetime.now().timestamp()}@example.com
DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}
DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
END:VEVENT
END:VCALENDAR
"""
    new_event = calendar.add_event(event)
    print(f"Event '{summary}' created with UID: {new_event.instance.vevent.uid.value}")
    return new_event.instance.vevent.uid.value

def get_event_by_uid(calendar, uid, start_time):
    events = calendar.date_search(start=start_time, end=start_time + timedelta(hours=1))
    for event in events:
        if uid in event.data:
            return event
    print(f"No event found with UID: {uid}")
    return None

def edit_event(event, new_start_time=None, new_end_time=None, new_summary=None, new_description=None, new_location=None):
    component = event.vobject_instance.vevent
    if new_start_time:
        component.dtstart.value = new_start_time
    if new_end_time:
        component.dtend.value = new_end_time
    if new_summary:
        component.summary.value = new_summary
    if new_description:
        component.description.value = new_description
    if new_location:
        component.location.value = new_location
    event.save()
    print(f"Event '{component.summary.value}' edited.")

def delete_event(event):
    event.delete()
    print(f"Event deleted.")

# Example usage:
calendar = calendars[0]  # Select the first calendar

# Create a new event and get its UID
start_time = datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.utc)
event_uid = create_event(
    calendar,
    start_time=start_time,
    end_time=datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.utc),
    summary="New Event",
    description="This is a new event",
    location="Location"
)

# Retrieve the event by UID and edit it
event = get_event_by_uid(calendar, event_uid, start_time)
if event:
    edit_event(
        event,
        new_summary="Edited Event",
        new_description="This event has been edited",
        new_location="New Location"
    )

    # Delete the event
    delete_event(event)