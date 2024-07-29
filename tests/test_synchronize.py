from potatotime.services import StubEvent, CreatedEvent
from potatotime.services.gcal import GoogleCalendarService
from potatotime.services.outlook import MicrosoftCalendarService
from potatotime.synchronize import synchronize
from utils import TIMEZONE
import datetime
import pytz


def test_copy_event():
    """
    Tests at a basic level that events are copied from one calendar to the other
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events, _ = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events[(0, 1)] + new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_copy_recurring_event():
    """
    Tests that recurring events are copied over
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data['recurrence'] = ['RRULE:FREQ=WEEKLY;COUNT=2']
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data['recurrence'] = {
        "pattern": {
            "type": "weekly",
            "interval": 1,  # Every week
            "daysOfWeek": ["friday"],  # Adjust based on the actual start day of the event
            "firstDayOfWeek": "friday"
        },
        "range": {
            "type": "numbered",
            "numberOfOccurrences": 2,
            "startDate": "2024-08-02"
        }
    }
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events, _ = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events[(0, 1)]) == 2, f"Expected 2 sync'ed events from Google to Microsoft. Got: {len(new_events[(0, 1)])}"
    assert len(new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events from Microsoft to Google. Got: {len(new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_copy_all_day_event():
    """
    Tests that all/multi-day events are copied successfully
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 0, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 3, 0, 0, 0)),
        is_all_day=True,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    # NOTE: Microsoft needs date-aligned datetimes in order for all-day event
    # creation to succeed.
    microsoft_event_data = StubEvent(
        start=datetime.datetime(2024, 8, 2, 0, 0, 0, tzinfo=pytz.utc),
        end=datetime.datetime(2024, 8, 4, 0, 0, 0, tzinfo=pytz.utc),
        is_all_day=True,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events, _ = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events[(0, 1)] + new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_update_edited_event():
    """
    Tests whether updates to edited events propagate to their sync'ed copies.
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events1, updated_events1 = synchronize([google_service, microsoft_service])

    google_update_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 3, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 3, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_update_data = google_service.update_event(google_event.id, google_update_data, is_copy=False)
    google_update = CreatedEvent.deserialize(google_update_data, google_service.event_serializer)

    microsoft_update_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 4, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 4, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_update_data = microsoft_service.update_event(microsoft_event.id, microsoft_update_data)
    microsoft_update = CreatedEvent.deserialize(microsoft_update_data, microsoft_service.event_serializer)

    new_events2, updated_events2 = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        microsoft_service.delete_event(event.id)

    # Check that update from Google to Microsoft calendar worked
    assert len(new_events1[(0, 1)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(updated_events2[(0, 1)]) == 1, f"Expected 1 updated events. Got: {len(new_events1[(0, 1)])}"
    assert StubEvent.from_(updated_events2[(0, 1)][0]) == StubEvent.from_(google_update)

    # Check that update from Microsoft to Google calendar worked
    assert len(new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(updated_events2[(1, 0)]) == 1, f"Expected 1 updated events. Got: {len(new_events1[(0, 1)])}"
    assert StubEvent.from_(updated_events2[(1, 0)][0]) == StubEvent.from_(microsoft_update)


def test_remove_deleted_event():
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events1, _ = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    microsoft_service.delete_event(microsoft_event.id)

    synchronize([google_service, microsoft_service])

    # Check that update from Google to Microsoft calendar worked
    assert len(new_events1[(0, 1)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0


def test_already_copied_event_microsoft():
    """
    Tests whether Microsoft events properly track (a) that it was createad by
    PotatoTime and (b) the source event
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    google_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 1, 11, 0, 0)),
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    new_events1, _ = synchronize([google_service, microsoft_service])
    new_events2, _ = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        google_service.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)] + new_events1[(1, 0)])}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"
    assert StubEvent.from_(new_events1[(0, 1)][0]) == StubEvent.from_(google_event)


def test_already_copied_event_google():
    """
    Tests whether Google events properly track (a) that it was createad by
    PotatoTime and (b) the source event
    """
    google_service = GoogleCalendarService()
    google_service.authorize()

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()

    assert len(google_service.get_events()) == 0
    assert len(microsoft_service.get_events()) == 0

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events1, _ = synchronize([microsoft_service, google_service])
    new_events2, _ = synchronize([microsoft_service, google_service])

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        microsoft_service.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        google_service.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)] + new_events1[(1, 0)])}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"
    assert StubEvent.from_(new_events1[(0, 1)][0]) == StubEvent.from_(microsoft_event)


# # TODO: automate setting up then declining an event
# def test_ignore_declined_google():
#     google_service = GoogleCalendarService()
#     google_service.authorize()

#     microsoft_service = MicrosoftCalendarService()
#     microsoft_service.authorize()

#     assert len(microsoft_service.get_events()) == 0

#     new_events, _ = synchronize([google_service, microsoft_service])
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"


# # # TODO: automate setting up then declining an event
# def test_ignore_declined_microsoft():
#     google_service = GoogleCalendarService()
#     google_service.authorize()

#     microsoft_service = MicrosoftCalendarService()
#     microsoft_service.authorize()

#     assert len(google_service.get_events()) == 0

#     new_events, _ = synchronize([google_service, microsoft_service])
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"


if __name__ == '__main__':
    test_copy_event()
    test_copy_recurring_event()
    test_copy_all_day_event()
    test_remove_deleted_event()
    test_update_edited_event()
    test_already_copied_event_microsoft()
    test_already_copied_event_google()

    # TODO: finish these tests
    # test_ignore_declined_google() # Need to finish writing test
    # test_ignore_declined_microsoft() # Need to get working