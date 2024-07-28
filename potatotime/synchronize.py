from typing import List
from .services import CalendarServiceInterface, CalendarEvent


def synchronize(calendars: List[CalendarServiceInterface]):
    # TODO: handle more than 100 events
    calendars_events = [
        list(map(calendar.CalendarEvent.deserialize, calendar.get_events()))
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
    events1: List[CalendarEvent],
    calendar2: CalendarServiceInterface,
    events2: List[CalendarEvent]
) -> List[str]:
    source_event_ids = {event.source_event_id for event in events2}

    new_events = []
    for event1 in events1:
        # Do not copy any events that were created by potatotime
        if event1.source_event_id is not None:
            continue

        # Do not copy any events that have already been copied
        if event1.id in source_event_ids:
            continue

        # TODO: distinguish between stubs and fully materialized events with ids
        event2_data = calendar2.CalendarEvent.from_(event1).serialize()
        event2_data.pop('id')  # stub would not have had this id
        event2_data = calendar2.create_event(event2_data, source_event_id=event1.id)
        event2 = calendar2.CalendarEvent.deserialize(event2_data)
        new_events.append(event2)
    return new_events