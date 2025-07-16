# PotatoTime

Synchronize events between Google, Outlook, and iCal.

## Install
```bash
pip install potatotime
```

## Quickstart
```python
from potatotime.services.gcal import GoogleService
from potatotime.services.outlook import MicrosoftService
from potatotime.synchronize import synchronize

google = GoogleService(); google.authorize("user")
microsoft = MicrosoftService(); microsoft.authorize("user")

synchronize([google.get_calendar(), microsoft.get_calendar()])
```

## Development
```bash
pip install -e .[test]
py.test --cov -x
```
