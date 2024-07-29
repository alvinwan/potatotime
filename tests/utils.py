import pytz

# Do not pass this into tzinfo= in the datetime constructor. Per the pytz
# documentation, https://pythonhosted.org/pytz/#example-usage:
# 
#   Unfortunately using the tzinfo argument of the standard datetime
#   constructors ‘’does not work’’ with pytz for many timezones.
#
TIMEZONE = pytz.timezone('US/Pacific')