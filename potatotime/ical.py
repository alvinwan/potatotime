import caldav
from datetime import datetime, timedelta
import os

# Connect to iCloud calendar
client = caldav.DAVClient(
    url='https://caldav.icloud.com/',
    username=os.environ['POTATOTIME_APPLE_USERNAME'],
    password=os.environ['POTATOTIME_APPLE_PASSWORD'],
)

# Fetch principal
principal = client.principal()

# List all calendars
calendars = principal.calendars()

# Fetch events from each calendar
for calendar in calendars:
    print(f"Fetching events from calendar: {calendar.name}")
    events = calendar.date_search(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now() + timedelta(days=30)
    )
    
    for event in events:
        print(event.data)