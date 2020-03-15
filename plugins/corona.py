from spanky.plugin import hook
import requests

base = "https://corona.lmao.ninja/"


def handle_countries():
    data = requests.get(base + "countries").json()
    ret = dict()
    for country in data:
        ret[country["country"].lower()] = country
    return ret


@hook.command()
def corona(text, reply):
    """<option> - available options: [all, <country name>]. If option is <country name>, you must specify a country from <https://worldometers.info/coronavirus#countries>. """

    args = text.split(" ")
    if len(args) == 0:
        reply("Usage: `.corona <option>`")
        return

    if args[0] == "all" or args[0] == "total":
        response = requests.get(base + "all").json()
        reply(
            f"""`Cases: {response['cases']} | Recovered: {response['recovered']}| Deaths: {response['deaths']}`""")
        return

    countries = handle_countries()

    if text.lower() not in countries:
        reply(
            "Country not found. Check out <https://worldometers.info/coronavirus#countries> for a complete list of countries.")
        return
    country_data = countries[text.lower()]

    reply(f"""`Cases: {country_data['cases']} (+{country_data['todayCases']} today) | Recovered: {country_data['recovered']} | Critical: {country_data['critical']} | Deaths: {country_data['deaths']} (+{country_data['todayDeaths']} today) `""")
