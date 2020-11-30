import random
import requests

from SpankyWorker import hook

types = ['trivia', 'math', 'date', 'year']


@hook.command(autohelp=False)
def fact(reply):
    """- Gets a random fact about numbers or dates."""
    fact_type = random.choice(types)
    try:
        json = requests.get('http://numbersapi.com/random/{}?json'.format(fact_type)).json()
    except Exception:
        reply("There was an error contacting the numbersapi.com API.")
        raise

    response = json['text']
    return response
