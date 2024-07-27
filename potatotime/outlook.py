import os
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Replace these values with your app's client ID, client secret, and redirect URI
CLIENT_ID = os.environ['POTATOTIME_MSFT_CLIENT_ID']
CLIENT_SECRET = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
AUTHORITY = 'https://login.microsoftonline.com/common'
AUTHORIZATION_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/authorize'
TOKEN_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/token'
SCOPES = ['Calendars.ReadWrite']

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

def get_auth_code():
    auth_url = f'{AUTHORIZATION_ENDPOINT}?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={" ".join(SCOPES)}'
    webbrowser.open(auth_url)

    httpd = HTTPServer(('localhost', 8080), OAuthHandler)
    httpd.handle_request()
    return httpd.auth_code

def get_token(auth_code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'scope': ' '.join(SCOPES),
    }
    response = requests.post(TOKEN_ENDPOINT, data=data)
    response.raise_for_status()
    return response.json()

def create_event(access_token, event_data):
    url = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, json=event_data)
    response.raise_for_status()
    return response.json()

def update_event(access_token, event_id, update_data):
    url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.patch(url, headers=headers, json=update_data)
    response.raise_for_status()
    return response.json()

def delete_event(access_token, event_id):
    url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.status_code

def main():
    if os.path.exists('msft.json'):
        with open('msft.json', 'r') as f:
            access_token = json.loads(f.read())['access_token']
    else:
        auth_code = get_auth_code()
        token_response = get_token(auth_code)
        access_token = token_response['access_token']
        with open('msft.json', 'w') as f:
            f.write(json.dumps({'access_token': access_token}))

    # Now you can use the access token to access the Outlook Calendar API
    calendar_api_url = 'https://graph.microsoft.com/v1.0/me/events'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Example: Create an event
    event_data = {
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
    created_event = create_event(access_token, event_data)
    print(f'Created event: {created_event["webLink"]}')

    # Example: Update the created event
    update_data = {
        "subject": "Discuss the new project - Updated",
    }
    updated_event = update_event(access_token, created_event['id'], update_data)
    print(f'Updated event: {updated_event["webLink"]}')

    # Example: Delete the created event
    delete_status = delete_event(access_token, created_event['id'])
    print(f'Delete status: {delete_status}')

if __name__ == '__main__':
    main()
