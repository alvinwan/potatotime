import datetime
import os
import webbrowser
import requests
import json
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from googleapiclient import errors
from abc import ABC, abstractmethod


class CalendarServiceInterface(ABC):
    @abstractmethod
    def authorize(self):
        pass

    @abstractmethod
    def create_event(self, event_data):
        pass

    @abstractmethod
    def update_event(self, event_id, update_data):
        pass

    @abstractmethod
    def delete_event(self, event_id):
        pass


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
            print('Event deleted.')
        except errors.HttpError as error:
            print(f'An error occurred: {error}')


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
        else:
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

    def create_event(self, event_data):
        url = 'https://graph.microsoft.com/v1.0/me/events'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, json=event_data)
        response.raise_for_status()
        return response.json()

    def update_event(self, event_id, update_data):
        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.patch(url, headers=headers, json=update_data)
        response.raise_for_status()
        return response.json()

    def delete_event(self, event_id):
        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
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


def main():
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

    microsoft_service = MicrosoftCalendarService()
    microsoft_service.authorize()
    
    microsoft_event_data = {
        "subject": "Discuss the new project",
        "body": {
            "contentType": "HTML",
            "content": "Let's discuss the new project on Thursday."
        },
        "start": {
            "dateTime": "2024-08-01T10:00:00",
            "timeZone": "Pacific Standard Time"
        },
        "end": {
            "dateTime": "2024-08-01T11:00:00",
            "timeZone": "Pacific Standard Time"
        },
        "location": {
            "displayName": "Conference Room"
        }
    }

    microsoft_event = microsoft_service.create_event(microsoft_event_data)
    microsoft_update_data = {
        "subject": "Discuss the new project - Updated",
    }
    microsoft_service.update_event(microsoft_event['id'], microsoft_update_data)
    microsoft_service.delete_event(microsoft_event['id'])


if __name__ == '__main__':
    main()