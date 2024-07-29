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
        recurrence=None,
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 10, 0, 0)),
        end=TIMEZONE.localize(datetime.datetime(2024, 8, 2, 11, 0, 0)),
        recurrence=None,
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events)}"

    copied_microsoft_event = new_events[(0, 1)][0]
    assert copied_microsoft_event.start == google_event.start.astimezone(pytz.utc)
    assert copied_microsoft_event.end == google_event.end.astimezone(pytz.utc)

    copied_google_event = new_events[(1, 0)][0]
    assert copied_google_event.start.astimezone(pytz.utc) == microsoft_event.start
    assert copied_google_event.end.astimezone(pytz.utc) == microsoft_event.end


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
        recurrence=None,
        is_all_day=True,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    # NOTE: Microsoft needs date-aligned datetimes in order for all-day event
    # creation to succeed.
    microsoft_event_data = StubEvent(
        start=datetime.datetime(2024, 8, 2, 0, 0, 0, tzinfo=pytz.utc),
        end=datetime.datetime(2024, 8, 4, 0, 0, 0, tzinfo=pytz.utc),
        recurrence=None,
        is_all_day=True,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_service.delete_event(event.id)

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events)}"

    copied_microsoft_event = new_events[(0, 1)][0]
    assert copied_microsoft_event.start == google_event.start.astimezone(pytz.utc)
    assert copied_microsoft_event.end == google_event.end.astimezone(pytz.utc)
    assert copied_microsoft_event.is_all_day

    copied_google_event = new_events[(1, 0)][0]
    assert copied_google_event.start.astimezone(pytz.utc) == microsoft_event.start
    assert copied_google_event.end.astimezone(pytz.utc) == microsoft_event.end
    assert copied_google_event.is_all_day


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
        recurrence=None,
        is_all_day=False,
    ).serialize(google_service.event_serializer)
    google_event_data = google_service.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_service.event_serializer)

    new_events1 = synchronize([google_service, microsoft_service])

    new_events2 = synchronize([google_service, microsoft_service])

    google_service.delete_event(google_event.id, is_copy=False)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        google_service.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        microsoft_service.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1)}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"

    copied_microsoft_event = new_events1[(0, 1)][0]
    assert copied_microsoft_event.start == google_event.start.astimezone(pytz.utc)
    assert copied_microsoft_event.end == google_event.end.astimezone(pytz.utc)


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
        recurrence=None,
        is_all_day=False,
    ).serialize(microsoft_service.event_serializer)
    microsoft_event_data = microsoft_service.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_service.event_serializer)

    new_events1 = synchronize([microsoft_service, google_service])

    new_events2 = synchronize([microsoft_service, google_service])

    microsoft_service.delete_event(microsoft_event.id)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        microsoft_service.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        google_service.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1)}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"

    copied_google_event = new_events1[(0, 1)][0]
    assert copied_google_event.start == microsoft_event.start.astimezone(pytz.utc)
    assert copied_google_event.end == microsoft_event.end.astimezone(pytz.utc)


# # TODO: automate setting up then declining an event
# def test_ignore_declined_google():
#     google_service = GoogleCalendarService()
#     google_service.authorize()

#     microsoft_service = MicrosoftCalendarService()
#     microsoft_service.authorize()

#     assert len(microsoft_service.get_events()) == 0

#     new_events = synchronize([google_service, microsoft_service])
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"


# # # TODO: automate setting up then declining an event
# def test_ignore_declined_microsoft():
#     google_service = GoogleCalendarService()
#     google_service.authorize()

#     microsoft_service = MicrosoftCalendarService()
#     microsoft_service.authorize()

#     assert len(google_service.get_events()) == 0

#     new_events = synchronize([google_service, microsoft_service])
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"


if __name__ == '__main__':
    test_copy_event()
    test_copy_all_day_event()
    test_already_copied_event_microsoft()
    test_already_copied_event_google()

    # TODO: finish these tests
    # test_ignore_declined_google() # Need to finish writing test
    # test_ignore_declined_microsoft() # Need to get working

    # TODO: add these tests
    # test_cannot_update_user_event()
    # test_cannot_delete_user_event()
    # test_update_event() # make sure updates propogate
    # test_copy_recurring_event()
    # test_copy_past_recurring_event()
    pass