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
    """<option> [country] - available options: [all, country]. If option is country, you must specify a country from <https://worldometers.info/coronavirus#countries>. """

    args = text.split(" ")
    if len(args) == 0:
        reply("Usage: `.corona <option> [countries]`")
        return

    if args[0] == "all" or args[0] == "total":
        response = requests.get(base + "all").json()
        reply(f"""```Coronavirus total:
Cases: {response['cases']}
Deaths: {response['deaths']}
Recovered: {response['recovered']}```""")

    elif args[0] == "country" or args[0] == "tara":
        if len(args) != 2:
            reply(f"usage: `.corona {args[0]} [countries]`")
            return

        countries = handle_countries()
        country_name = args[1]
        if country_name.lower() not in countries:
            reply(
                "Country not found. Check out <https://worldometers.info/coronavirus#countries> for a complete list of countries.")
            return
        country_data = countries[country_name.lower()]

        reply(f"""```{country_data['country']}:
Total cases: {country_data['cases']}
Today's cases: {country_data['todayCases']}
Total deaths: {country_data['deaths']}
Today's deaths: {country_data['todayDeaths']}
Total recovered: {country_data['recovered']}
Total critical: {country_data['critical']}```""")
