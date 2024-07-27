import os
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer

# Replace these values with your app's client ID, client secret, and redirect URI
CLIENT_ID = os.environ['POTATOTIME_MSFT_CLIENT_ID']
CLIENT_SECRET = os.environ['POTATOTIME_MSFT_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8080'
AUTHORITY = 'https://login.microsoftonline.com/common'
AUTHORIZATION_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/authorize'
TOKEN_ENDPOINT = f'{AUTHORITY}/oauth2/v2.0/token'
SCOPES = ['Calendars.Read']

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

def main():
    auth_code = get_auth_code()
    token_response = get_token(auth_code)
    access_token = token_response['access_token']
    print(f'Access token: {access_token}')

    # Now you can use the access token to access the Outlook Calendar API
    calendar_api_url = 'https://graph.microsoft.com/v1.0/me/calendar/events'
    headers = {'Authorization': f'Bearer {access_token}'}
    events_response = requests.get(calendar_api_url, headers=headers)
    events_response.raise_for_status()
    events = events_response.json()
    print(events)

if __name__ == '__main__':
    main()