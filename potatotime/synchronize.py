from typing import List
from .services import CalendarInterface, ExtendedEvent, StubEvent
import datetime


def synchronize(
    calendars: List[CalendarInterface],
    max_days: int=365,
    max_events: int=1000
):
    start = datetime.datetime.utcnow()
    end = start + datetime.timedelta(days=max_days)
    calendars_events = [
        [
            ExtendedEvent.deserialize(event_data, calendar.event_serializer)
            for event_data in calendar.get_events(start=start, end=end, max_events=max_events)
        ]
        for calendar in calendars
    ]

    created, updated, deleted = {}, {}, {}
    for i in range(len(calendars)):
        for j in range(len(calendars)):
            if i == j:
                continue
            created[(i, j)], updated[(i, j)], deleted[(i, j)] = \
                synchronize_from_to(calendars[i], calendars_events[i], calendars[j], calendars_events[j])
    return created, updated, deleted


def synchronize_from_to(
    calendar1: CalendarInterface,
    events1: List[ExtendedEvent],
    calendar2: CalendarInterface,
    events2: List[ExtendedEvent]
) -> List[str]:
    source_event_ids = {
        event.source_event_id: event for event in events2
        if event.source_event_id
    }

    created, updated, deleted = [], [], []
    for event1 in events1:
        # Handle edited events
        if event1.id in source_event_ids:  # events already sync'ed
            event2 = source_event_ids.pop(event1.id)
            copy_stub = StubEvent.from_(event2)
            orig_stub = StubEvent.from_(event1)
            if copy_stub == orig_stub:  # if still equal to original, we're done
                continue

            copy_data = orig_stub.serialize(calendar2.event_serializer)
            copy_data = calendar2.update_event(event2.id, copy_data)
            copy = ExtendedEvent.deserialize(copy_data, calendar2.event_serializer)
            updated.append(copy)

        # Handle newly-created events
        if (  # Do not copy any of the following events
            event1.source_event_id is not None  # copy created by PotatoTime
            or event1.declined  # event declined by user (only implemented for Google)
        ):
            continue

        copy2_data = StubEvent.from_(event1).serialize(calendar2.event_serializer)
        copy2_data = calendar2.create_event(copy2_data, source_event_id=event1.id)
        copy2 = ExtendedEvent.deserialize(copy2_data, calendar2.event_serializer)
        created.append(copy2)

    # Handle deleted events
    for event in source_event_ids.values():
        deleted.append(event)
        calendar2.delete_event(event.id)

    return created, updated, deleted