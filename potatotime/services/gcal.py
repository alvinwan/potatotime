import datetime
import os.path
from googleapiclient import errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from . import CalendarServiceInterface, CalendarEvent
from typing import Optional


class GoogleCalendarEvent(CalendarEvent):
    def serialize(self) -> dict:
        return {
            'id': self.id,
            'start': {'dateTime': self.start.isoformat()},
            'end': {'dateTime': self.end.isoformat()},
            'recurrence': self.recurrence,
            'htmlLink': self.url
        }

    @staticmethod
    def deserialize(event_data: dict):
        return GoogleCalendarEvent(
            id=event_data.get('id'),
            start=datetime.datetime.fromisoformat(event_data['start']['dateTime']),
            end=datetime.datetime.fromisoformat(event_data['end']['dateTime']),
            url=event_data['htmlLink'],
            recurrence=event_data.get('recurrence', []),
            source_event_id=event_data.get('extendedProperties', {}).get('private', {}).get('potatotime')
        )


class GoogleCalendarService(CalendarServiceInterface):
    CalendarEvent = GoogleCalendarEvent
    
    def __init__(self):
        # If modifying these SCOPES, delete the file goog.json.
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

    def create_event(self, event_data: dict, source_event_id: Optional[str]):
        if source_event_id is not None:  # NOTE: Should only be None during testing
            event_data['extendedProperties'] = {'private': {'potatotime': source_event_id}}
        event = self.service.events().insert(calendarId='primary', body=event_data).execute()
        print(f'Event created: {event.get("htmlLink")}')
        return event

    def update_event(self, event_id, update_data):
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        assert 'potatotime' in event.get('extendedProperties', {}).get('private', {})
        event.update(update_data)
        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        print(f'Event updated: {updated_event.get("htmlLink")}')
        return updated_event

    def delete_event(self, event_id, is_copy: bool=True):
        if is_copy:  # NOTE: Should only be False during testing
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            assert 'potatotime' in event.get('extendedProperties', {}).get('private', {})
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f'Event "{event_id}" deleted.')
        except errors.HttpError as error:
            print(f'An error occurred: {error}')
