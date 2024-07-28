import datetime
import os.path
from googleapiclient import errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from . import CalendarServiceInterface


# If modifying these SCOPES, delete the file goog.json.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]

class GoogleCalendarService(CalendarServiceInterface):
    def __init__(self):
        self.scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]

    def authorize(self):
        creds = None
        if os.path.exists('goog.json'):
            creds = Credentials.from_authorized_user_file('goog.json', self.scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.scopes)
                creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
            with open('goog.json', 'w') as token:
                token.write(creds.to_json())
        self.service = build('calendar', 'v3', credentials=creds)
    
    def get_events(self):
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = self.service.events().list(calendarId='primary', timeMin=now,
                                                   maxResults=100, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])
        return events

    def create_event(self, event_data):
        event = self.service.events().insert(calendarId='primary', body=event_data).execute()
        print(f'Event created: {event.get("htmlLink")}')
        return event['id']

    def update_event(self, event_id, update_data):
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        event.update(update_data)
        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        print(f'Event updated: {updated_event.get("htmlLink")}')

    def delete_event(self, event_id):
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f'Event "{event_id}" deleted.')
        except errors.HttpError as error:
            print(f'An error occurred: {error}')
