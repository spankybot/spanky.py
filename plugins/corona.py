from spanky.plugin import hook
import requests

base = "https://corona.lmao.ninja/"

country_codes = {
    'ae': 'uae',
    'al': 'albania',
    'at': 'austria',
    'au': 'australia',
    'ba': 'bosnia and herzegovina',
    'be': 'belgium',
    'bg': 'bulgaria',
    'br': 'brazil',
    'bw': 'botswana',
    'by': 'belarus',
    'ca': 'canada',
    'ch': 'switzerland',
    'cn': 'china',
    'cy': 'cyprus',
    'cz': 'czechia',
    'de': 'germany',
    'dk': 'denmark',
    'dp': 'diamond princess',
    'ee': 'estonia',
    'eg': 'egypt',
    'es': 'spain',
    'fi': 'finland',
    'fr': 'france',
    'gb': 'uk',
    'ge': 'georgia',
    'gr': 'greece',
    'hk': 'hong kong',
    'hu': 'hungary',
    'ie': 'ireland',
    'in': 'india',
    'iq': 'iraq',
    'ir': 'iran',
    'is': 'iceland',
    'it': 'italy',
    'jp': 'japan',
    'kr': 's. korea',
    'md': 'moldova',
    'nl': 'netherlands',
    'no': 'norway',
    'nz': 'new zealand',
    'pe': 'peru',
    'ph': 'philippines',
    'pk': 'pakistan',
    'pl': 'poland',
    'pt': 'portugal',
    'ro': 'romania',
    'ru': 'russia',
    'sa': 'saudi arabia',
    'se': 'sweden',
    'si': 'slovenia',
    'sk': 'slovakia',
    'th': 'thailand',
    'vatican': 'vatican city',
}


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

    if text.lower() in country_codes:
        text = country_codes[text.lower()]

    if text.lower() not in countries:
        reply(
            "Country not found. Check out <https://worldometers.info/coronavirus#countries> for a complete list of countries.")
        return
    country_data = countries[text.lower()]

    reply(f"""`Cases: {country_data['cases']} (+{country_data['todayCases']} today) | Recovered: {country_data['recovered']} | Critical: {country_data['critical']} | Deaths: {country_data['deaths']} (+{country_data['todayDeaths']} today) `""")
