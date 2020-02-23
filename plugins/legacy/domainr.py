import requests
from spanky.plugin import hook

formats = {
    "taken": "\x034{domain}\x0f{path}",
    "available": "\x033{domain}\x0f{path}",
    "other": "\x031{domain}\x0f{path}"
}

def format_domain(domain):
    """
    :type domain: dict[str, str]
    """
    if domain["availability"] in formats:
        domainformat = formats[domain["availability"]]
    else:
        domainformat = formats["other"]
    return domainformat.format(**domain)

@hook.command
def domain(text):
    """<domain> - uses domain.nr's API to search for a domain, and similar domains
    :type text: str
    """
    try:
        data = requests.get('http://domai.nr/api/json/search?q=' + text).json()
    except :
        return "Unable to get data for some reason. Try again later."
    if "query" not in data.keys() or data['query'] == "":
        return "An error occurred: {status} - {message}".format(**data['error'])

    domains = [format_domain(domain) for domain in data["results"]]
    return "Domains: {}".format(", ".join(domains))
