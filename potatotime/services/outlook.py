import os
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import datetime
import pytz
from . import ServiceInterface, CalendarInterface, EventSerializer, BaseEvent, POTATOTIME_EVENT_SUBJECT, POTATOTIME_EVENT_DESCRIPTION
from potatotime.storage import Storage, FileStorage
from typing import Optional, List, Dict


class _MicrosoftEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name in ('start', 'end'):
            field_value = getattr(event, field_name)
            return field_name, {
                'dateTime': field_value.isoformat(),
                'timeZone': getattr(field_value.tzinfo, 'zone', field_value.tzname()) if field_value.tzinfo else 'UTC'
            }
        if field_name == 'is_all_day':
            return 'isAllDay', event.is_all_day
        raise NotImplementedError(f"Serializing {field_name} is not supported")
    
    def deserialize(self, field_name: str, event_data: dict):
        if field_name == 'id':
            return event_data.get('id')
        if field_name in ('start', 'end'):
            time = datetime.datetime.fromisoformat(event_data[field_name]['dateTime'])
            timezone = pytz.timezone(event_data[field_name]['timeZone'])
            time = timezone.localize(time)
            return time
        if field_name == 'url':
            return event_data.get('webLink')
        if field_name == 'source_event_id':
            return event_data.get('singleValueExtendedProperties', [{}])[0].get('value')
        if field_name == 'declined':
            # TODO: Not fully implemented. Pass the user's email address to finish implementing
            return any([
                attendee['status']['response'] == 'declined' and attendee['emailAddress']['address'] == None
                for attendee in event_data.get('attendees', [])
            ])
        if field_name == 'is_all_day':
            return event_data.get('isAllDay', False)


class MicrosoftService(ServiceInterface):

    def __init__(self):
        self.client_id = os.environ['POTATOTIME_MSFT_CLIENT_ID']
        self.client_secret = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
        self.redirect_uri = 'http://localhost:8080'
        self.authorization_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.token_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.scopes = ['Calendars.ReadWrite', 'offline_access']
        self.event_serializer = _MicrosoftEventSerializer()

    def authorize(self, user_id: str, storage: Storage=FileStorage()):
        if storage.has_user_credentials(user_id):
            credentials = storage.get_user_credentials(user_id)
            self.access_token = credentials['access_token']
            self.refresh_token = credentials.get('refresh_token')

            # Try to use the access token
            url = "https://graph.microsoft.com/v1.0/me/events"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 401:
                # Access token might be expired, refresh it
                self._refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return

        # If no valid access token or refresh token, start authorization flow
        auth_code = self._get_auth_code()
        token_response = self._get_token(auth_code)
        self.access_token = token_response['access_token']
        self.refresh_token = token_response.get('refresh_token')
        storage.save_user_credentials(user_id, json.dumps({
            'access_token': self.access_token,
            'refresh_token': self.refresh_token
        }))

    def _get_auth_code(self):
        auth_url = f'{self.authorization_endpoint}?client_id={self.client_id}&response_type=code&redirect_uri={self.redirect_uri}&scope={" ".join(self.scopes)}'
        webbrowser.open(auth_url)
        httpd = HTTPServer(('localhost', 8080), OAuthHandler)
        httpd.handle_request()
        return httpd.auth_code

    def _get_token(self, auth_code):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
        }
        response = requests.post(self.token_endpoint, data=data)
        response.raise_for_status()
        return response.json()
    
    def _refresh_token(self, refresh_token):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'scope': ' '.join(self.scopes),
        }
        response = requests.post(self.token_endpoint, data=data)
        response.raise_for_status()
        return response.json()
    
    def _refresh_access_token(self):
        if not hasattr(self, 'refresh_token'):
            raise ValueError("No refresh token available. Please authenticate first.")
        token_response = self._refresh_token(self.refresh_token)
        self.access_token = token_response.get('access_token')
        self.refresh_token = token_response.get('refresh_token', self.refresh_token)
        return token_response
    
    def list_calendars(self) -> List[Dict]:
        url = "https://graph.microsoft.com/v1.0/me/calendars"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        calendar_list = response.json()
        return calendar_list.get('value', [])
    
    # TODO: duplicated from GoogleCalendar
    def get_calendar(self, calendar_id: Optional[str]=None):
        calendars = self.list_calendars()
        for calendar in calendars:
            if calendar['id'] == calendar_id or calendar_id is None:
                return MicrosoftCalendar(self, calendar)
        raise ValueError(f'Invalid calendar_id: {calendar_id}')
    

class MicrosoftCalendar(CalendarInterface):
    def __init__(self, service, calendar_id):
        self.service = service
        self.calendar_id = calendar_id
        self.event_serializer = _MicrosoftEventSerializer()
    
    def get_events(
        self,
        start: Optional[datetime.datetime]=None,
        end: Optional[datetime.datetime]=None,
        max_events: int=1000,
        results_per_page: int=100,
    ):
        url = 'https://graph.microsoft.com/v1.0/me/calendarView'
        headers = {
            'Authorization': f'Bearer {self.service.access_token}'
        }
        
        if not start:
            start = datetime.datetime.utcnow()
        if not end:
            end = start + datetime.timedelta(days=30)
        
        params = {
            'startDateTime': start.isoformat() + 'Z',
            'endDateTime': end.isoformat() + 'Z',
            '$orderby': 'start/dateTime',
            '$top': results_per_page,
            '$expand': "singleValueExtendedProperties($filter=id eq 'String {66f5a359-4659-4830-9070-00040ec6ac6e} Name potatotime')",
        }
        
        events = []
        next_link = None

        while True:
            if next_link:
                response = requests.get(next_link, headers=headers)
            else:
                response = requests.get(url, headers=headers, params=params)

            response.raise_for_status()
            response_data = response.json()
            events.extend(response_data.get('value', []))
            
            # Check if we have reached the maximum number of events
            if len(events) >= max_events:
                events = events[:max_events]
                break
            
            # Check if there's a next page
            next_link = response_data.get('@odata.nextLink')
            if not next_link:
                break
        
        return events

    def create_event(self, event_data: dict, source_event_id: Optional[str]):
        url = 'https://graph.microsoft.com/v1.0/me/events'
        headers = {
            'Authorization': f'Bearer {self.service.access_token}',
            'Content-Type': 'application/json'
        }
        event_data['subject'] = POTATOTIME_EVENT_SUBJECT
        event_data['body'] = {
            "contentType": "HTML",
            "content": POTATOTIME_EVENT_DESCRIPTION
        }
        event_data["singleValueExtendedProperties"] = [{
            "id": "String {66f5a359-4659-4830-9070-00040ec6ac6e} Name potatotime",
            "value": source_event_id,
        }]
        response = requests.post(url, headers=headers, json=event_data)
        response.raise_for_status()
        event = response.json()
        print(f"Event created: {event['webLink']}")
        return event

    def update_event(self, event_id, update_data):
        # TODO: check the event is potatotime-created
        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        headers = {
            'Authorization': f'Bearer {self.service.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.patch(url, headers=headers, json=update_data)
        response.raise_for_status()
        event = response.json()
        print(f"Event updated: {event['webLink']}")
        return event

    def delete_event(self, event_id):
        # TODO: check the event is potatotime-created
        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        headers = {
            'Authorization': f'Bearer {self.service.access_token}'
        }
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f'Event "{event_id}" deleted.')
        return response.status_code

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'You can close this window now.')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Authorization failed.')
