from spanky.plugin import hook
import requests
from datetime import datetime

base = "https://corona.lmao.ninja/v2/"


def getFormat(author, storage):
    if author.id in storage:
        return storage[author.id]
    return "`Country | Cases | Recovered | Critical | Deaths | Active | Tests | Last updated at LUpdated`"


@hook.command()
def corona(text, reply, storage, author):
    """<option> - available options: [all, <country name>]. If option is <country name>, you must specify a country from <https://worldometers.info/coronavirus#countries>. """

    args = text.split(" ")
    if len(args) == 0:
        reply("Usage: `.corona <option>`")
        return

    if args[0] == "all" or args[0] == "total" or text == "":
        country_data = requests.get(base + "all").json()
    else:
        country_data = requests.get(base + "countries/" + text).json()

    # if the return data has a message field, it means something occured and we should print it
    if "message" in country_data:
        reply(country_data["message"])
        return

    if "country" not in country_data:
        country_data["country"] = "World"

    if "continent" not in country_data:
        country_data["continent"] = "Worldwide"

    userFormat = getFormat(author, storage)
    data = {
        "Cases": f"Cases: {country_data['cases']:,} (CToday)",
        "Deaths": f"Deaths: {country_data['deaths']:,} (DToday)",
        "Tests": f"Tests: {country_data['tests']:,}",
        "CToday": f"+{country_data['todayCases']:,} today",
        "DToday": f"+{country_data['todayDeaths']:,} today",
        "C/M": f"Cases/1M: {country_data['casesPerOneMillion']:,}",
        "D/M": f"Deaths/1M: {country_data['deathsPerOneMillion']:,}",
        "T/M": f"Tests/1M: {country_data['testsPerOneMillion']:,}",
        "Recovered": f"Recovered: {country_data['recovered']:,}",
        "Active": f"Active: {country_data['active']:,}",
        "Critical": f"Critical: {country_data['critical']:,}",
        "Country": country_data["country"],
        "Continent": country_data["continent"],
        "LUpdated": datetime.utcfromtimestamp(country_data["updated"] // 1000).strftime(
            "%Y-%m-%d at %H:%M:%S UTC"
        ),
    }

    for key, value in data.items():
        print(key, value)
        userFormat = userFormat.replace(key, value)
    reply(f"{userFormat}")


@hook.command()
def corona_format(text, reply, storage, author):
    """<format> - formats the .corona command for you. Every keyword in ['Cases', 'Deaths', 'Tests', 'CToday', 'DToday', 'C/M', 'D/M', 'T/M', 'Recovered', 'Active', 'Critical', 'Country', 'Continent', 'LUpdated'] will be replaced with the appropriate data. Use `clear` if you want to clear your format and use the default one"""
    if text == "help":
        reply(corona_format.__doc__)
        return
    if text == "":
        reply(f"Your format: {getFormat(author, storage)}")
        return
    if text == "clear":
        if author.id in storage:
            storage.pop(author.id, None)
            reply("Format cleared!")
        else:
            reply("You don't have a custom format set")
        return
    storage[author.id] = text
    reply("Format set!")
