import requests

from spanky.plugin import hook

url = 'http://www.discuvver.com/jump2.php'
headers = {'Referer': 'http://www.discuvver.com'}


@hook.command('randomusefulsite')
def randomusefulwebsite():
    response = requests.head(url, headers=headers, allow_redirects=True)
    response.raise_for_status()
    return response.url
