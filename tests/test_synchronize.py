from potatotime.services.gcal import GoogleCalendarService, GoogleCalendarEvent
from potatotime.services.outlook import MicrosoftCalendarService, MicrosoftCalendarEvent
from potatotime.synchronize import synchronize
import datetime
import pytz


def test_copy_event():
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    google_event_data = GoogleCalendarEvent(
        start=datetime.datetime(2024, 8, 1, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 1, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
    ).serialize()
    google_event_data = google_service.create_event(google_event_data)
    google_event = GoogleCalendarEvent.deserialize(google_event_data)

    microsoft_event_data = MicrosoftCalendarEvent(
        start=datetime.datetime(2024, 8, 2, 10, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
        end=datetime.datetime(2024, 8, 2, 11, 0, 0, tzinfo=pytz.timezone('America/Los_Angeles')),
    ).serialize()
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data)
    microsoft_event = MicrosoftCalendarEvent.deserialize(microsoft_event_data)

    new_events = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events) == 2

    copied_microsoft_event = new_events[(0, 1)][0]
    assert copied_microsoft_event.start == google_event.start.astimezone(pytz.utc)
    assert copied_microsoft_event.end == google_event.end.astimezone(pytz.utc)

    copied_google_event = new_events[(1, 0)][0]
    assert copied_google_event.start.astimezone(pytz.utc) == microsoft_event.start
    assert copied_google_event.end.astimezone(pytz.utc) == microsoft_event.end


if __name__ == '__main__':
    test_copy_event()

    # TODO: add these tests
    # test_already_copied_event()
    # test_copy_recurring_event()
    # test_copy_past_recurring_event()