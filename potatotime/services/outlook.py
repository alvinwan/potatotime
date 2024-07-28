import os
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import datetime
import pytz
from . import CalendarServiceInterface, CalendarEvent

# Replace these values with your app's client ID, client secret, and redirect URI
CLIENT_ID = os.environ['POTATOTIME_MSFT_CLIENT_ID']
CLIENT_SECRET = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
AUTHORITY = 'https://login.microsoftonline.com/common'
AUTHORIZATION_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/authorize'
TOKEN_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/token'
SCOPES = ['Calendars.ReadWrite']

class MicrosoftCalendarService(CalendarServiceInterface):
    def __init__(self):
        self.client_id = os.environ['POTATOTIME_MSFT_CLIENT_ID']
        self.client_secret = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
        self.redirect_uri = 'http://localhost:8080'
        self.authorization_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.token_endpoint = f'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.scopes = ['Calendars.ReadWrite']

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
            '$top': 100
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        events = response.json().get('value', [])
        return events

    def create_event(self, event_data):
        url = 'https://graph.microsoft.com/v1.0/me/events'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=event_data)
        response.raise_for_status()
        event = response.json()
        print(f"Event created: {event['webLink']}")
        return event

    def update_event(self, event_id, update_data):
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


class MicrosoftCalendarEvent(CalendarEvent):
    # TODO: Add support for recurrence rules

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'start': {
                'dateTime': self.start.isoformat(),
                'timeZone': self.start.tzinfo.tzname(self.start) if self.start.tzinfo else 'UTC'
            },
            'end': {
                'dateTime': self.end.isoformat(),
                'timeZone': self.end.tzinfo.tzname(self.end) if self.end.tzinfo else 'UTC'
            },
            'webLink': self.url,
        }

    @staticmethod
    def deserialize(event_data: dict):
        start_time = datetime.datetime.fromisoformat(event_data['start']['dateTime'])
        end_time = datetime.datetime.fromisoformat(event_data['end']['dateTime'])
        
        start_timezone = pytz.timezone(event_data['start']['timeZone'])
        end_timezone = pytz.timezone(event_data['end']['timeZone'])

        start_time = start_time.replace(tzinfo=start_timezone)
        end_time = end_time.replace(tzinfo=end_timezone)

        return MicrosoftCalendarEvent(
            id=event_data['id'],
            start=start_time,
            end=end_time,
            url=event_data['webLink'],
        )