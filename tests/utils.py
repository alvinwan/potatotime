import pytz
import os

# Do not pass this into tzinfo= in the datetime constructor. Per the pytz
# documentation, https://pythonhosted.org/pytz/#example-usage:
# 
#   Unfortunately using the tzinfo argument of the standard datetime
#   constructors ‘’does not work’’ with pytz for many timezones.
#
TIMEZONE = pytz.timezone('US/Pacific')

TEST_GOOGLE_USER_ID = os.environ.get('POTATOTIME_TEST_GOOGLE_USER_ID', 'default_google')
TEST_MICROSOFT_USER_ID = os.environ.get('POTATOTIME_TEST_MICROSOFT_USER_ID', 'default_microsoft')