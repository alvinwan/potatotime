import os
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import datetime
import pytz
from . import CalendarServiceInterface, EventSerializer, BaseEvent
from typing import Optional

# Replace these values with your app's client ID, client secret, and redirect URI
CLIENT_ID = os.environ['POTATOTIME_MSFT_CLIENT_ID']
CLIENT_SECRET = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
AUTHORITY = 'https://login.microsoftonline.com/common'
AUTHORIZATION_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/authorize'
TOKEN_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/token'
SCOPES = ['Calendars.ReadWrite']
    

class _MicrosoftEventSerializer(EventSerializer):
    def serialize(self, field_name: str, event: BaseEvent):
        if field_name == 'recurrence':
            return None # TODO: implement me
        if field_name in ('start', 'end'):
            field_value = getattr(event, field_name)
            return {
                'dateTime': field_value.isoformat(),
                'timeZone': field_value.tzinfo.tzname(field_value) if field_value.tzinfo else 'UTC'
            }
        raise NotImplementedError(f"Serializing {field_name} is not supported")
    
    def deserialize(self, field_name: str, event_data: dict):
        if field_name == 'id':
            return event_data.get('id')
        if field_name in ('start', 'end'):
            time = datetime.datetime.fromisoformat(event_data[field_name]['dateTime'])
            timezone = pytz.timezone(event_data[field_name]['timeZone'])
            time = time.replace(tzinfo=timezone)
            return time
        if field_name == 'url':
            return event_data.get('webLink')
        if field_name == 'recurrence':
            return None # TODO: implement me
        if field_name == 'source_event_id':
            return event_data.get('singleValueExtendedProperties', [{}])[0].get('value')


class MicrosoftCalendarService(CalendarServiceInterface):

    def __init__(self):
        self.client_id = os.environ['POTATOTIME_MSFT_CLIENT_ID']
        self.client_secret = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
        self.redirect_uri = 'http://localhost:8080'
        self.authorization_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.token_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.scopes = ['Calendars.ReadWrite']
        self.event_serializer = _MicrosoftEventSerializer()

    def authorize(self):
        if os.path.exists('msft.json'):
            with open('msft.json', 'r') as f:
                self.access_token = json.loads(f.read())['access_token']

            url = "https://graph.microsoft.com/v1.0/me/events"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return

        auth_code = self._get_auth_code()
        token_response = self._get_token(auth_code)
        self.access_token = token_response['access_token']
        with open('msft.json', 'w') as f:
            f.write(json.dumps({'access_token': self.access_token}))

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
    
    def get_events(self):
        url = 'https://graph.microsoft.com/v1.0/me/events'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        params = {
            '$filter': f'start/dateTime ge \'{datetime.datetime.utcnow().isoformat()}\'',
            '$orderby': 'start/dateTime',
            '$top': 100,
            '$expand': "singleValueExtendedProperties($filter=id eq 'String {66f5a359-4659-4830-9070-00040ec6ac6e} Name potatotime')",
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        events = response.json().get('value', [])
        return events

    def create_event(self, event_data: dict, source_event_id: Optional[str]):
        url = 'https://graph.microsoft.com/v1.0/me/events'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
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
            'Authorization': f'Bearer {self.access_token}',
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
            'Authorization': f'Bearer {self.access_token}'
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
