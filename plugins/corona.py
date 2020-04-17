from spanky.plugin import hook
import requests

base = "https://corona.lmao.ninja/v2/"

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
    'us': 'usa',
    'vatican': 'vatican city',
}


def handle_countries():
    data = requests.get(base + "countries").json()
    ret = dict()
    for country in data:
        ret[country["country"].lower()] = country
    return ret


def getFormat(author, storage):
    if author.id in storage:
        return storage[author.id]
    return "`Cases | Recovered | Critical | Deaths | Active | Information updated multiple times a day`"


@hook.command()
def corona(text, reply, storage, author):
    """<option> - available options: [all, <country name>]. If option is <country name>, you must specify a country from <https://worldometers.info/coronavirus#countries>. """

    args = text.split(" ")
    if len(args) == 0:
        reply("Usage: `.corona <option>`")
        return

    if args[0] == "all" or args[0] == "total" or text == "":
        response = requests.get(base + "all").json()
        reply(
            f"""`Cases: {response['cases']} | Recovered: {response['recovered']} | Deaths: {response['deaths']} | Information updated multiple times a day.`""")
        return

    countries = handle_countries()

    if text.lower() in country_codes:
        text = country_codes[text.lower()]

    if text.lower() not in countries:
        reply("Country not found. Either the command is dead, or you need to check out <https://worldometers.info/coronavirus#countries> for a complete list of countries.")
        return
    country_data = countries[text.lower()]

    userFormat = getFormat(author, storage)

    data = {
        "Cases": f"Cases: {country_data['cases']} (+{country_data['todayCases']} today)",
        "Recovered": f"Recovered: {country_data['recovered']}",
        "Critical": f"Critical: {country_data['critical']}",
        "Deaths": f"Deaths: {country_data['deaths']} (+{country_data['todayDeaths']} today)",
        "Active": f"Active: {country_data['active']}",
        "C/M": f"Cases/1M: {country_data['casesPerOneMillion']}"
    }

    for key, value in data.items():
        print(key, value)
        userFormat = userFormat.replace(key, value, 1)
    reply(f"{userFormat}")


@hook.command()
def corona_format(text, reply, storage, author):
    """<format> - formats the .corona command for you. Every keyword in ["Cases", "Recovered", "Critical", "Deaths", "Active", "C/M"] will be replaced with the appropriate data.
    Use `clear` if you want to clear your format and use the default one"""
    if text == "help":
        reply("Usage: `.corona_format <format>`\nMore information in the `.help` section for the command")
        return
    if text == "":
        reply(f"Your format: {getFormat(author, storage)}")
        return
    if text == "clear":
        storage.pop(author.id, None)
        reply("Format cleared!")
        return
    storage[author.id] = text
    reply("Format set!")
