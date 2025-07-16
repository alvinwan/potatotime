# PotatoTime

Synchronize events between Google, Outlook, and iCal.


```bash
pip install -e .
```

## Quickstart

To get started, setup OAuth credentials for each service.

- To obtain the Google client file, create an OAuth Desktop Application in
the Google Cloud Console and download the JSON credentials. Save this as
`potatotime_client_google.json`.

- For Microsoft, register an app in the Azure Portal and note the
Application (client) ID and secret. Set these values in the environment
variables `POTATOTIME_MSFT_CLIENT_ID` and
`POTATOTIME_MSFT_CLIENT_SECRET` before authorizing.

Then, run the following script.

```python
from potatotime.services.gcal import GoogleService
from potatotime.services.outlook import MicrosoftService
from potatotime.synchronize import synchronize

google = GoogleService(); google.authorize("user")
microsoft = MicrosoftService(); microsoft.authorize("user")

synchronize([google.get_calendar(), microsoft.get_calendar()])
```

This will prompt you login to each service via the browser. The credentials will be stored in the current directory as `potatotime_user_{SERVICE}.json`
by default.

## Storage

The library stores credentials with a simple `FileStorage` by default.
User tokens are written to `potatotime_user_<USER_ID>.json` and OAuth
client details are read from `potatotime_client_<SERVICE>.json` in the
current directory.

You can also read credentials from environment variables using
`EnvStorage`:

```python
from potatotime.storage import EnvStorage

google = GoogleService(); google.authorize("user", storage=EnvStorage())
microsoft = MicrosoftService(); microsoft.authorize("user", storage=EnvStorage())
```

By default, this expects user tokens to be stored in environment variables
as `POTATOTIME_USER_{USER_ID}` and OAuth client details to be stored in
environment variables as `POTATOTIME_CLIENT_{SERVICE}`.

### Apple Calendar

Apple Calendar access requires a username and an app password:

```bash
export POTATOTIME_APPLE_USERNAME="your_apple_id@example.com"
export POTATOTIME_APPLE_PASSWORD="app-specific-password"
```

Generate the password from your Apple ID account page and supply your
Apple ID email address for the username.

## Development

Run all tests using the following.

```bash
pip install -e .[test]
py.test --cov -x
```
