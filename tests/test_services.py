from potatotime.services.gcal import GoogleCalendarService, GoogleCalendarEvent
from potatotime.services.outlook import MicrosoftCalendarService, MicrosoftCalendarEvent
from potatotime.services.ical import AppleCalendarService, AppleCalendarEvent
import datetime
import pytz


def test_raw_google_service():
    google_service = GoogleCalendarService()
    google_service.authorize()
    
    google_event_data = {
        'summary': 'Sample Event',
        'location': '800 Howard St., San Francisco, CA 94103',
        'description': 'A chance to hear more about Google\'s developer products.',
        'start': {
            'dateTime': '2024-08-01T09:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2024-08-01T17:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
        'recurrence': [
            'RRULE:FREQ=WEEKLY;COUNT=10'
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }

    google_event = google_service.create_event(google_event_data)
    google_update_data = {
        'summary': 'Updated Sample Event',
        'location': '500 Terry A Francois Blvd, San Francisco, CA 94158',
        'description': 'A chance to hear more about Google\'s updated developer products.',
        'start': {
            'dateTime': '2024-08-02T10:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2024-08-02T18:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
    }
    google_service.update_event(google_event['id'], google_update_data)

    for event in google_service.get_events():
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event.get('summary'))

    google_service.delete_event(google_event['id'])


def test_google_service():
    google_service = GoogleCalendarService()
    google_service.authorize()
    
    google_event_data = GoogleCalendarEvent(
        start=datetime.datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        recurrence='RRULE:FREQ=WEEKLY;COUNT=10'
    ).serialize()

    google_event = GoogleCalendarEvent.deserialize(
        google_service.create_event(google_event_data)
    )
    google_update_data = GoogleCalendarEvent(
        start=datetime.datetime(2024, 8, 2, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 2, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        recurrence=''
    ).serialize()
    google_service.update_event(google_event.id, google_update_data)

    for event_data in google_service.get_events():
        event = GoogleCalendarEvent.deserialize(event_data)
        print(event.id, event.start, event.end)

    google_service.delete_event(google_event.id)


def test_raw_microsoft_service():
    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()
    
    microsoft_event_data = {
        "subject": "Discuss the new project",
        "body": {
            "contentType": "HTML",
            "content": "Let's discuss the new project on Thursday."
        },
        "start": {
            "dateTime": "2024-08-01T10:00:00",
            "timeZone": "Pacific Standard Time"
        },
        "end": {
            "dateTime": "2024-08-01T11:00:00",
            "timeZone": "Pacific Standard Time"
        },
        "location": {
            "displayName": "Conference Room"
        }
    }

    microsoft_event_id = microsoft_service.create_event(microsoft_event_data)
    microsoft_update_data = {
        "subject": "Discuss the new project - Updated",
    }
    microsoft_service.update_event(microsoft_event_id, microsoft_update_data)

    for event in microsoft_service.get_events():
        print(event['start']['dateTime'], event['subject'])

    microsoft_service.delete_event(microsoft_event_id)


def test_microsoft_service():
    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    microsoft_event_data = MicrosoftCalendarEvent(
        start=datetime.datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
    ).serialize()

    microsoft_event_id = microsoft_service.create_event(microsoft_event_data)
    microsoft_update_data = MicrosoftCalendarEvent(
        start=datetime.datetime(2024, 8, 2, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 2, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
    ).serialize()
    microsoft_service.update_event(microsoft_event_id, microsoft_update_data)

    for event_data in microsoft_service.get_events():
        event = MicrosoftCalendarEvent.deserialize(event_data)
        print(event.id, event.start, event.end)

    microsoft_service.delete_event(microsoft_event_id)


def test_raw_apple_service():
    apple_service = AppleCalendarService()
    apple_service.authorize()
    
    apple_event_data = {
        'start': datetime.datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.utc),
        'end': datetime.datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.utc),
        'summary': "New Event",
        'description': "This is a new event",
        'location': "Location"
    }
    apple_event = apple_service.create_event(apple_event_data)
    apple_update_data = {
        'start': datetime.datetime(2024, 8, 2, 10, 0, 0, tzinfo=pytz.utc),
        'end': datetime.datetime(2024, 8, 2, 11, 0, 0, tzinfo=pytz.utc),
        'summary': "Edited Event",
        'description': "This event has been edited",
        'location': "New Location"
    }
    apple_service.update_event(apple_event, apple_update_data)

    for event in apple_service.get_events():
        component = event.instance.vevent
        print(component.dtstart.value, component.summary.value)

    apple_service.delete_event(apple_event)


def test_apple_service():
    apple_service = AppleCalendarService()
    apple_service.authorize()

    apple_event_data = AppleCalendarEvent(
        start=datetime.datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.utc),
        end=datetime.datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.utc),
    ).serialize()
    apple_event = apple_service.create_event(apple_event_data)
    apple_update_data = AppleCalendarEvent(
        start=datetime.datetime(2024, 8, 2, 10, 0, 0, tzinfo=pytz.utc),
        end=datetime.datetime(2024, 8, 2, 11, 0, 0, tzinfo=pytz.utc),
    ).serialize()
    apple_service.update_event(apple_event, apple_update_data)

    for event_data in apple_service.get_events():
        event = AppleCalendarEvent.deserialize(event_data)
        print(event.id, event.start, event.end)

    apple_service.delete_event(apple_event)


if __name__ == '__main__':
    # TODO: make these into real tests
    test_raw_google_service()
    test_google_service()
    test_raw_microsoft_service()
    test_microsoft_service()
    test_raw_apple_service()
    test_apple_service()