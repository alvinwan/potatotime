import os
import requests
import json
import datetime
import pytz
from . import ServiceInterface, CalendarInterface, EventSerializer, BaseEvent, POTATOTIME_EVENT_SUBJECT, POTATOTIME_EVENT_DESCRIPTION
from potatotime.storage import Storage, FileStorage
from typing import Optional, List, Dict
from msal import ConfidentialClientApplication, SerializableTokenCache
from .auth import get_auth_code


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
        self.scopes = ['Calendars.ReadWrite']
        self.event_serializer = _MicrosoftEventSerializer()

        self.cache = SerializableTokenCache()
        self.app = ConfidentialClientApplication(
            self.client_id,
            authority='https://login.microsoftonline.com/common',
            client_credential=self.client_secret,
            token_cache=self.cache,
        )
        self.access_token = None

    def authorize(self, user_id: str, storage: Storage=FileStorage(), interactive: bool=True):
        accounts = []
        if storage.has_user_credentials(user_id):
            # NOTE: Technically, this one cache should be used to globally
            # contain all accounts. 'Sharding' cache across files in case there
            # are many accounts.
            self.cache.deserialize(storage.get_user_credentials(user_id))
            accounts = self.app.get_accounts()
            
        if accounts:
            account = accounts[0]  # assumes only one account per
            result = self.app.acquire_token_silent(self.scopes, account)  # handles refreshing access token
            self.access_token = result['access_token']
            storage.save_user_credentials(user_id, self.cache.serialize())

        if not self.access_token and interactive:
            auth_url = self.app.get_authorization_request_url(self.scopes, redirect_uri=self.redirect_uri)
            auth_code = get_auth_code(auth_url)
            token_response = self.app.acquire_token_by_authorization_code(
                auth_code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            self.access_token = token_response['access_token']
            storage.save_user_credentials(user_id, self.cache.serialize())
        
        if not self.access_token:
            raise Exception('No credentials found, or credentials are expired.')
    
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
