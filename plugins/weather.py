from fractions import Fraction
from typing import Optional

import googlemaps
import collections
from forecastiopy.ForecastIO import ForecastIO
from googlemaps.exceptions import ApiError
from sqlalchemy import Table, Column, PrimaryKeyConstraint, String

from spanky.plugin import hook
from spanky.utils import web
from spanky import database

Api = Optional[googlemaps.Client]


class PluginData:
    maps_api = None  # type: Api


data = PluginData()
ds_key = None

# Define database table

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

    # Derived from values from http://snowfence.umn.edu/Components/winddirectionanddegreeswithouttable3.htm
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


def add_location(user, location, storage):
    if "locations" not in storage:
        storage["locations"] = {}
        storage.sync()
    storage["locations"][str(user.id)] = str(location).lower()
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


def get_location(user, storage):
    """looks in location_cache for a saved location"""
    if "locations" not in storage:
        return
    if user.id not in storage["locations"]:
        return
    return storage["locations"][user.id]


def check_and_parse(user, text, storage):
    """
    Check for the API keys and parse the location from user input
    """
    if not ds_key:
        return None, "This command requires a DarkSky API key."

    if not data.maps_api:
        return None, "This command requires a Google Developers Console API key."

    if not text:
        location = get_location(user, storage)
        if not location:
            return None, weather.__doc__
    else:
        location = text
        add_location(user, location, storage)
    print("loc=" + location)

    # use find_location to get location data from the user input
    try:
        location_data = find_location(location, bias=None)
    except ApiError:
        return None, "API Error occurred."
        raise

    fio = ForecastIO(
        ds_key,
        units=ForecastIO.UNITS_US,
        latitude=location_data["lat"],
        longitude=location_data["lng"],
    )

    return (location_data, fio), None


@hook.command(autohelp=False, aliases=["we"])
def weather(reply, event, text, send_embed, storage):
    """<location> - Gets weather data for <location>."""
    res, err = check_and_parse(event.author, text, storage)
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

    send_embed("Weather for " + location_data["address"], "", reply)
