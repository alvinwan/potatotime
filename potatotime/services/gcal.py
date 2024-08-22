import datetime
import os.path
from urllib.error import HTTPError
from googleapiclient import errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from potatotime.services import ServiceInterface, CalendarInterface, EventSerializer, BaseEvent, POTATOTIME_EVENT_SUBJECT, POTATOTIME_EVENT_DESCRIPTION
from potatotime.services.auth import get_auth_code
from potatotime.storage import Storage, FileStorage
from typing import Optional, List, Dict, Union
import pytz
import json


class _GoogleEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name in ('start', 'end'):
            field_value = getattr(event, field_name)
            if event.is_all_day:
                return field_name, {'date': field_value.strftime('%Y-%m-%d') }
            return field_name, {
                'dateTime': field_value.isoformat(),
                'timeZone': getattr(field_value.tzinfo, 'zone', field_value.tzname()) if field_value.tzinfo else 'UTC'
            }
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
        if field_name == 'source_event_id':
            return event_data.get('extendedProperties', {}).get('private', {}).get('potatotime')
        if field_name == 'declined':
            return any([attendee.get('self') and attendee['responseStatus'] == 'declined'
                        for attendee in event_data.get('attendees', [])])
        if field_name == 'is_all_day':
            return 'date' in event_data['start'] and 'date' in event_data['end']


class GoogleService(ServiceInterface):
    
    def __init__(self):
        # If modifying these SCOPES, delete the file goog.json.
        self.scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ]
        self.event_serializer = _GoogleEventSerializer()

    def authorize(self, user_id: str, storage: Storage=FileStorage(), interactive: bool=True):
        # TODO: This needs some major refactoring
        creds = None
        if storage.has_user_credentials(user_id):
            creds = Credentials.from_authorized_user_info(
                json.loads(storage.get_user_credentials(user_id)),
                self.scopes,
            )
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # TODO: what if refresh fails? Get an exception. Maybe instead
                # gracefully default to interactive?
                creds.refresh(Request())
            elif interactive:
                # TODO: replace str 'google' with constant
                flow = InstalledAppFlow.from_client_config(
                    json.loads(storage.get_client_credentials('google')),
                    self.scopes
                )
                flow.redirect_uri = 'http://localhost:5173/'
                auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
                auth_code = get_auth_code(auth_url, port=5173)
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
            try:
                storage.save_user_credentials(user_id, creds.to_json())
            except Exception as e:
                print(f"Failed to save updated credentials: {e}")

            if not creds:
                raise Exception('No credentials found, or credentials are expired.')
        self.service = build('calendar', 'v3', credentials=creds)

    def list_calendars(self) -> List[Dict]:
        try:
            calendar_list = self.service.calendarList().list().execute()
            return calendar_list.get('items', [])
        except HTTPError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_calendar(self, calendar_id: Optional[str]=None):
        calendars = self.list_calendars()
        for calendar in calendars:
            if calendar['id'] == calendar_id or calendar_id is None:
                return GoogleCalendar(self.service, calendar_id)
        raise ValueError(f'Invalid calendar_id: {calendar_id}')


class GoogleCalendar(CalendarInterface):

    def __init__(self, service, calendar_id):
        self.service = service
        self.calendar_id = calendar_id
        self.event_serializer = _GoogleEventSerializer()
    
    def get_events(
        self,
        start: Optional[datetime.datetime]=None,
        end: Optional[datetime.datetime]=None,
        max_events: int=1000,
        results_per_page: int=100,
    ):
        if not start:
            start = datetime.datetime.utcnow()
        if not end:
            end = start + datetime.timedelta(days=30)
        
        events = []
        page_token = None

        while True:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start.isoformat() + 'Z',
                timeMax=end.isoformat() + 'Z',
                maxResults=min(results_per_page, max_events - len(events)),  # Ensure we do not exceed max_events
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()

            events.extend(events_result.get('items', []))
            
            # Check if we have reached the maximum number of events
            if len(events) >= max_events:
                events = events[:max_events]
                break
            
            # Get the next page token, if there is one
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break

        return events

    def create_event(self, event_data: dict, source_event_id: Optional[str]):
        if source_event_id is not None:  # NOTE: Should only be None during testing
            event_data['extendedProperties'] = {'private': {'potatotime': source_event_id}}
        event_data['summary'] = POTATOTIME_EVENT_SUBJECT
        event_data['description'] = POTATOTIME_EVENT_DESCRIPTION
        event_data['colorId'] = '8'  # Light gray color
        event = self.service.events().insert(calendarId='primary', body=event_data).execute()
        print(f'Event created: {event.get("htmlLink")}')
        return event

    def update_event(self, event_id, update_data, is_copy: bool=True):
        event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        if is_copy:  # NOTE: Should only be False during testing
            assert 'potatotime' in event.get('extendedProperties', {}).get('private', {})
        event.update(update_data)
        updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        print(f'Event updated: {updated_event.get("htmlLink")}')
        return updated_event

    def delete_event(self, event_or_event_id: Union[str, dict], is_copy: bool=True):
        # TODO: Only this gcal implementation supports raw event_data dict. Update interface
        if isinstance(event_or_event_id, dict):
            event = event_or_event_id
            event_id = event['id']
        else:
            event_id = event_or_event_id
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
        if is_copy:  # NOTE: Should only be False during testing
            assert 'potatotime' in event.get('extendedProperties', {}).get('private', {})
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            print(f'Event "{event_id}" deleted.')
        except errors.HttpError as error:
            print(f'An error occurred: {error}')


if __name__ == '__main__':
    service = GoogleService()
    service.authorize('default_google')  # TODO: use constant for user_id