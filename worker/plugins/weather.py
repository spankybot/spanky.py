from fractions import Fraction
from typing import Optional

import googlemaps
import collections

from forecastiopy.ForecastIO import ForecastIO
from googlemaps.exceptions import ApiError

from core import hook

Api = Optional[googlemaps.Client]


class PluginData:
    maps_api = None  # type: Api


data = PluginData()
ds_key = None

location_cache = []

BEARINGS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)

# math constants
NUM_BEARINGS = len(BEARINGS)
BEARING_SECTION = 360 / NUM_BEARINGS
BEARING_RANGE = BEARING_SECTION / 2


def bearing_to_card(bearing):
    if bearing > 360 or bearing < 0:
        raise ValueError("Invalid wind bearing: {}".format(bearing))

    # Derived from values from
    # http://snowfence.umn.edu/Components/winddirectionanddegreeswithouttable3.htm
    index = int(NUM_BEARINGS * (((bearing + BEARING_RANGE) % 360) / 360))
    return BEARINGS[index]


def convert_f2c(temp):
    """
    Convert temperature in Fahrenheit to Celsios
    """
    return float((temp - 32) * Fraction(5, 9))


def mph_to_kph(mph):
    return mph * 1.609344


def find_location(location, bias=None):
    """
    Takes a location as a string, and returns a dict of data
    :param location: string
    :param bias: The region to bias answers towards
    :return: dict
    """
    json = data.maps_api.geocode(location, region=bias)[0]
    out = json["geometry"]["location"]
    out["address"] = json["formatted_address"]
    return out


def add_location(nick, location, storage):
    if storage["data"] is None:
        storage["data"] = {}

    storage["data"][nick] = str(location)
    storage.sync()


@hook.on_start()
def create_maps_api(bot):
    global ds_key

    google_key = bot.config.get("api_keys", {}).get("google_dev_key", None)

    if google_key:
        data.maps_api = googlemaps.Client(google_key)
    else:
        data.maps_api = None

    ds_key = bot.config.get("api_keys", {}).get("darksky", None)


def get_location(nick, storage):
    """
    looks in location_cache for a saved location
    """
    if not storage["data"]:
        storage["data"] = {}
        return None

    if nick in storage["data"]:
        return storage["data"][nick]


def check_and_parse(nick, text, storage):
    """
    Check for the API keys and parse the location from user input
    """
    if not ds_key:
        return None, "This command requires a DarkSky API key."

    if not data.maps_api:
        return None, "This command requires a Google Developers Console API key."

    # If no input try the db
    if not text:
        location = get_location(nick, storage)
        if not location:
            return weather.__doc__
    else:
        location = text
        add_location(nick, location, storage)

    # use find_location to get location data from the user input
    try:
        location_data = find_location(location, bias=None)
    except ApiError:
        return "API Error occurred."
        raise

    fio = ForecastIO(
        ds_key,
        units=ForecastIO.UNITS_US,
        latitude=location_data["lat"],
        longitude=location_data["lng"],
    )

    return (location_data, fio), None


@hook.command()
def weather(reply, event, text, reply_embed, storage):
    """<location> - Gets weather data for <location>."""
    res, err = check_and_parse(event.author.name, text, storage)

    if not res:
        return err

    location_data, fio = res

    daily_conditions = fio.get_daily()["data"]
    current = fio.get_currently()
    today, tomorrow, *three_days = daily_conditions[:5]

    reply = collections.OrderedDict()
    reply[
        "Current"
    ] = "{summary}, {temp:.0f}C; Humidity: {humidity:.0%}; Wind: {wind_speed:.0f}KPH {wind_direction}".format(
        summary=current["summary"],
        temp=convert_f2c(current["temperature"]),
        humidity=current["humidity"],
        wind_speed=mph_to_kph(current["windSpeed"]),
        wind_direction=bearing_to_card(current["windBearing"]),
    )

    today["name"] = "Today"
    tomorrow["name"] = "Tomorrow"

    for day_fc in (today, tomorrow):
        reply[
            day_fc["name"]
        ] = "\n {summary}; High: {temp_high:.0f}C; Low: {temp_low:.0f}C; Humidity: {humidity:.0%}".format(
            day=day_fc["name"],
            summary=day_fc["summary"],
            temp_high=convert_f2c(day_fc["temperatureHigh"]),
            temp_low=convert_f2c(day_fc["temperatureLow"]),
            humidity=day_fc["humidity"],
        )

    reply_embed(
        title="Weather for " + location_data["address"],
        description="",
        fields=reply
    )
