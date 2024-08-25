from potatotime.services import StubEvent, CreatedEvent
from potatotime.services.gcal import GoogleService
from potatotime.services.outlook import MicrosoftService
from potatotime.synchronize import synchronize
from utils import TIMEZONE, TEST_GOOGLE_USER_ID, TEST_MICROSOFT_USER_ID
import datetime
import pytz


NOW = datetime.datetime.now().replace(second=0, microsecond=0)
TMW_START = NOW + datetime.timedelta(days=1)
TMW_END = NOW + datetime.timedelta(days=1, hours=1)
DAT_START = NOW + datetime.timedelta(days=2) # "Day After Tomorrow" xD
DAT_END = NOW + datetime.timedelta(days=2, hours=1)
TMW_DAY = TMW_START.replace(hour=0, minute=0, second=0, microsecond=0)
DAT_DAY = DAT_START.replace(hour=0, minute=0, second=0, microsecond=0)


def check_clean_calendar(calendar):
    # Check the next few days are clean. Just a degenerate check for tests
    assert len(calendar.get_events(max_events=1, end=datetime.datetime.now() + datetime.timedelta(days=3))) == 0


def test_copy_event():
    """
    Tests at a basic level that events are copied from one calendar to the other
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_calendar.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_calendar.delete_event(event.id)

    microsoft_calendar.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_calendar.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events[(0, 1)] + new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_copy_recurring_event():
    """
    Tests that recurring events are copied over
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_event_data['recurrence'] = ['RRULE:FREQ=WEEKLY;COUNT=2']
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    dotw = DAT_START.strftime("%A").lower()
    microsoft_event_data['recurrence'] = {
        "pattern": {
            "type": "weekly",
            "interval": 1,  # Every week
            "daysOfWeek": [dotw],
            "firstDayOfWeek": dotw,
        },
        "range": {
            "type": "numbered",
            "numberOfOccurrences": 2,
            "startDate": DAT_START.strftime("%Y-%m-%d"),
        }
    }
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=14) # include next two occurrences

    google_calendar.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_calendar.delete_event(event.id)

    microsoft_calendar.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_calendar.delete_event(event.id)

    assert len(new_events[(0, 1)]) == 2, f"Expected 2 sync'ed events from Google to Microsoft. Got: {len(new_events[(0, 1)])}"
    assert len(new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events from Microsoft to Google. Got: {len(new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_copy_all_day_event():
    """
    Tests that all/multi-day events are copied successfully
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_DAY),
        end=TIMEZONE.localize(TMW_DAY + datetime.timedelta(days=1)),
        is_all_day=True,
    ).serialize(google_calendar.event_serializer)
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    # NOTE: Microsoft needs date-aligned datetimes in order for all-day event
    # creation to succeed.
    microsoft_event_data = StubEvent(
        start=datetime.datetime(DAT_DAY.year, DAT_DAY.month, DAT_DAY.day, 0, 0, 0, tzinfo=pytz.utc),
        end=datetime.datetime(DAT_DAY.year, DAT_DAY.month, DAT_DAY.day + 1, 0, 0, 0, tzinfo=pytz.utc),
        is_all_day=True,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_calendar.delete_event(google_event.id, is_copy=False)
    for event in new_events[(1, 0)]:
        google_calendar.delete_event(event.id)

    microsoft_calendar.delete_event(microsoft_event.id)
    for event in new_events[(0, 1)]:
        microsoft_calendar.delete_event(event.id)

    assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 2, f"Expected 2 sync'ed events. Got: {len(new_events[(0, 1)] + new_events[(1, 0)])}"
    assert StubEvent.from_(new_events[(0, 1)][0]) == StubEvent.from_(google_event)
    assert StubEvent.from_(new_events[(1, 0)][0]) == StubEvent.from_(microsoft_event)


def test_update_edited_event():
    """
    Tests whether updates to edited events propagate to their sync'ed copies.
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events1, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_update_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_update_data = google_calendar.update_event(google_event.id, google_update_data, is_copy=False)
    google_update = CreatedEvent.deserialize(google_update_data, google_calendar.event_serializer)

    microsoft_update_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_update_data = microsoft_calendar.update_event(microsoft_event.id, microsoft_update_data)
    microsoft_update = CreatedEvent.deserialize(microsoft_update_data, microsoft_calendar.event_serializer)

    created2, updated2, deleted2 = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_calendar.delete_event(google_event.id, is_copy=False)
    for event in new_events1[(1, 0)] + created2[(1, 0)]:
        google_calendar.delete_event(event.id)

    microsoft_calendar.delete_event(microsoft_event.id)
    for event in new_events1[(0, 1)] + created2[(0, 1)]:
        microsoft_calendar.delete_event(event.id)

    # Check that update from Google to Microsoft calendar worked
    assert len(new_events1[(0, 1)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(updated2[(0, 1)]) == 1, f"Expected 1 updated events. Got: {len(updated2[(0, 1)])}"
    assert len(created2[(0, 1)]) == 0, f"Expected 0 created events. Got: {len(created2[(0, 1)])}"
    assert StubEvent.from_(updated2[(0, 1)][0]) == StubEvent.from_(google_update)

    # Check that update from Microsoft to Google calendar worked
    assert len(new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(updated2[(1, 0)]) == 1, f"Expected 1 updated events. Got: {len(updated2[(0, 1)])}"
    assert len(created2[(1, 0)]) == 0, f"Expected 0 created events. Got: {len(created2[(0, 1)])}"
    assert StubEvent.from_(updated2[(1, 0)][0]) == StubEvent.from_(microsoft_update)


def test_remove_deleted_event():
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events1, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_calendar.delete_event(google_event.id, is_copy=False)
    microsoft_calendar.delete_event(microsoft_event.id)

    _, _, deleted_events2 = synchronize([google_calendar, microsoft_calendar], max_days=3)

    # Check that update from Google to Microsoft calendar worked
    assert len(new_events1[(0, 1)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)])}"
    assert len(deleted_events2[(1, 0)]) == 1, f"Expected 1 deleted events. Got: {len(deleted_events2[(1, 0)])}"
    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)


def test_already_copied_event_microsoft():
    """
    Tests whether Microsoft events properly track (a) that it was createad by
    PotatoTime and (b) the source event
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    google_event_data = StubEvent(
        start=TIMEZONE.localize(TMW_START),
        end=TIMEZONE.localize(TMW_END),
        is_all_day=False,
    ).serialize(google_calendar.event_serializer)
    google_event_data = google_calendar.create_event(google_event_data, source_event_id=None)
    google_event = CreatedEvent.deserialize(google_event_data, google_calendar.event_serializer)

    new_events1, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)
    new_events2, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)

    google_calendar.delete_event(google_event.id, is_copy=False)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        google_calendar.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        microsoft_calendar.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)] + new_events1[(1, 0)])}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"
    assert StubEvent.from_(new_events1[(0, 1)][0]) == StubEvent.from_(google_event)


def test_already_copied_event_google():
    """
    Tests whether Google events properly track (a) that it was createad by
    PotatoTime and (b) the source event
    """
    google_service = GoogleService()
    google_service.authorize(TEST_GOOGLE_USER_ID)
    google_calendar = google_service.get_calendar()

    microsoft_service = MicrosoftService()
    microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
    microsoft_calendar = microsoft_service.get_calendar()

    check_clean_calendar(google_calendar)
    check_clean_calendar(microsoft_calendar)

    microsoft_event_data = StubEvent(
        start=TIMEZONE.localize(DAT_START),
        end=TIMEZONE.localize(DAT_END),
        is_all_day=False,
    ).serialize(microsoft_calendar.event_serializer)
    microsoft_event_data = microsoft_calendar.create_event(microsoft_event_data, source_event_id=None)
    microsoft_event = CreatedEvent.deserialize(microsoft_event_data, microsoft_calendar.event_serializer)

    new_events1, _, _ = synchronize([microsoft_calendar, google_calendar], max_days=3)
    new_events2, _, _ = synchronize([microsoft_calendar, google_calendar], max_days=3)

    microsoft_calendar.delete_event(microsoft_event.id)
    for event in new_events1[(1, 0)] + new_events2[(1, 0)]:
        microsoft_calendar.delete_event(event.id)

    for event in new_events1[(0, 1)] + new_events2[(0, 1)]:
        google_calendar.delete_event(event.id)

    assert len(new_events1[(0, 1)] + new_events1[(1, 0)]) == 1, f"Expected 1 sync'ed events. Got: {len(new_events1[(0, 1)] + new_events1[(1, 0)])}"
    assert len(new_events2[(1, 0)]) == 0, f"Should not copy the copy PotatoTime made"
    assert len(new_events2[(0, 1)]) == 0, f"Should not sync the already-sync'ed event"
    assert StubEvent.from_(new_events1[(0, 1)][0]) == StubEvent.from_(microsoft_event)


# # TODO: automate setting up then declining an event
# def test_ignore_declined_google():
#     google_service = GoogleService()
#     google_service.authorize(TEST_GOOGLE_USER_ID)

#     microsoft_service = MicrosoftService()
#     microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
#     microsoft_calendar = microsoft_service.get_calendar()

#     check_clean_calendar(microsoft_calendar)

#     new_events, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"


# # # TODO: automate setting up then declining an event
# def test_ignore_declined_microsoft():
#     google_service = GoogleService()
#     google_service.authorize(TEST_GOOGLE_USER_ID)

#     microsoft_service = MicrosoftService()
#     microsoft_service.authorize(TEST_MICROSOFT_USER_ID)
#     microsoft_calendar = microsoft_service.get_calendar()

#     check_clean_calendar(google_calendar)

#     new_events, _, _ = synchronize([google_calendar, microsoft_calendar], max_days=3)
#     assert len(new_events[(0, 1)] + new_events[(1, 0)]) == 0, f"Expected 0 sync'ed events. Got: {len(new_events)}"
