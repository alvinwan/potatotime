from services.gcal import GoogleCalendarService


if __name__ == '__main__':
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

    google_event_id = google_service.create_event(google_event_data)
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
    google_service.update_event(google_event_id, google_update_data)
    google_service.delete_event(google_event_id)