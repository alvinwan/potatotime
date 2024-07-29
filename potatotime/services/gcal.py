import datetime
import os.path
from googleapiclient import errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from . import CalendarServiceInterface, EventSerializer, BaseEvent
from typing import Optional
import pytz


class _GoogleEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name == 'recurrence':
            return field_name, event.recurrence
        if field_name in ('start', 'end'):
            if event.is_all_day:
                return field_name, {'date': getattr(event, field_name).strftime('%Y-%m-%d') }
            return field_name, {'dateTime': getattr(event, field_name).isoformat()}
        if field_name == 'is_all_day':
            return None, None
        raise NotImplementedError(f"Serializing {field_name} is not supported")
    
    def deserialize(self, field_name: str, event_data: dict):
        if field_name == 'id':
            return event_data.get('id')
        if field_name in ('start', 'end'):
            field_value = event_data[field_name]
            if 'dateTime' in field_value:
                return datetime.datetime.fromisoformat(field_value['dateTime'])
            elif 'date' in field_value:
                return pytz.utc.localize(datetime.datetime.fromisoformat(field_value['date']))
            raise NotImplementedError('Unsupported start and end time format')
        if field_name == 'url':
            return event_data.get('htmlLink')
        if field_name == 'recurrence':
            return event_data.get('recurrence', [])
        if field_name == 'source_event_id':
            return event_data.get('extendedProperties', {}).get('private', {}).get('potatotime')
        if field_name == 'declined':
            return any([attendee.get('self') and attendee['responseStatus'] == 'declined'
                        for attendee in event_data.get('attendees', [])])
        if field_name == 'is_all_day':
            return 'date' in event_data['start'] and 'date' in event_data['end']


class GoogleCalendarService(CalendarServiceInterface):
    
    def __init__(self):
        # If modifying these SCOPES, delete the file goog.json.
        self.scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        self.event_serializer = _GoogleEventSerializer()

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
