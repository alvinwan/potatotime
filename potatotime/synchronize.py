from typing import List
from .services import CalendarServiceInterface, ExtendedEvent, StubEvent


def synchronize(calendars: List[CalendarServiceInterface]):
    # TODO: handle more than 100 events
    calendars_events = [
        [
            ExtendedEvent.deserialize(event_data, calendar.event_serializer)
            for event_data in calendar.get_events()
        ]
        for calendar in calendars
    ]

    new_events = {}
    for i in range(len(calendars)):
        for j in range(len(calendars)):
            if i == j:
                continue
            new_events[(i, j)] = synchronize_from_to(calendars[i], calendars_events[i], calendars[j], calendars_events[j])
    return new_events


def synchronize_from_to(
    calendar1: CalendarServiceInterface,
    events1: List[ExtendedEvent],
    calendar2: CalendarServiceInterface,
    events2: List[ExtendedEvent]
) -> List[str]:
    source_event_ids = {event.source_event_id for event in events2}

    new_events = []
    for event1 in events1:
        if (  # Do not copy any of the following events
            event1.source_event_id is not None  # copy created by PotatoTime
            or event1.id in source_event_ids  # events already sync'ed
            or event1.declined  # event declined by user (only implemented for Google)
        ):
            continue

        copy2_data = StubEvent.from_(event1).serialize(calendar2.event_serializer)
        copy2_data = calendar2.create_event(copy2_data, source_event_id=event1.id)
        copy2 = ExtendedEvent.deserialize(copy2_data, calendar2.event_serializer)
        new_events.append(copy2)
    return new_events