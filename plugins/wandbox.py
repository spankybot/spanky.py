import json
import re
import requests
from spanky.plugin import hook
from spanky.utils import web

compilers = []
compilers_proc = {}

MAX_LEN = 500
MAX_LINES = 10


def quote_it(data):
    import re

    return "```\n" + data + "\n```"


def extract_code(msg):
    msg = msg.strip()
    if msg == "":
        return None, None

    parts = msg.split("\n", 1)
    if len(parts) == 1:
        fl_parts = parts[0].split(None, 1)

        # just language specified, not code
        if len(fl_parts) == 1:
            return fl_parts[0], None

        lang, code = fl_parts

        # remove backticks (doesn't unescape other backticks)
        if code[0] == code[-1] == "`":
            code = code[1:-1]

        return lang, code

    # firs line should not have more than one word, which should be the language
    if len(parts[0].split()) > 1:
        return None, None

    # remove ``` from the end if we've got them
    code = parts[1]
    if code.endswith("\n```"):
        code = code[:-4]

    # handle ```<lang> when language was not specified
    lang = parts[0].strip()
    if lang.startswith("```"):
        lang = lang[3:]

    # remove ```[lang]
    elif code.startswith("```"):
        _, code = code.split("\n", 1)

    return lang, code


@hook.command()
def wb(text, send_message):
    """wandbox interface"""
    if len(compilers) == 0:
        request = requests.get("https://wandbox.org/api/list.json")
        for i in request.json():
            lang = i["language"].replace(" HEAD", "").split()[0].lower()
            if lang not in compilers_proc:
                compilers_proc[lang] = []
            compilers_proc[lang].append(i["name"])

        for i in compilers_proc:
            compilers_proc[i] = sorted(compilers_proc[i])
            compilers.append(compilers_proc[i][-1])

    lang, code = extract_code(text)

    if lang not in compilers and lang not in compilers_proc:
        msg = "Compilers: `" + ", ".join(i for i in sorted(compilers)) + "`\n"
        msg += "OR\n"
        msg += "Languages: `" + ", ".join(i for i in sorted(compilers_proc)) + "`\n"
        msg += "Run with: `.wb <compiler/language> <code>`"
        send_message(msg)
        return

    # Check if a compiler was specified instead of a language
    if lang not in compilers and lang in compilers_proc:
        lang = compilers_proc[lang][-1]

    req = {}
    req["compiler"] = lang
    req["code"] = code
    print(req)

    request = requests.post("https://wandbox.org/api/compile.json", json=req)

    resp = request.json()
    # print("asd" + str(resp))

    if "program_message" in resp:
        to_print = resp["program_message"]

    if "compiler_message" in resp:
        to_print = resp["compiler_message"]

    try:
        if to_print:
            to_print = re.sub(r"(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]", "", to_print)
            if len(to_print) > MAX_LEN and len(to_print.split("\n")) > MAX_LINES:
                url = web.paste(data=str(to_print))
                resp_lines = to_print.split("\n")
                return (
                    "```"
                    + "\n".join(resp_lines[:MAX_LINES])
                    + "```"
                    + " [...] see output at "
                    + url
                )

            if len(to_print) > MAX_LEN:
                url = web.paste(data=str(to_print))
                return (
                    "```" + to_print[:MAX_LEN] + "```" + " [...] see output at " + url
                )

            elif len(to_print.split("\n")) > MAX_LINES:
                url = web.paste(data=str(to_print))

                resp_lines = to_print.split("\n")

                return (
                    "```"
                    + "\n".join(resp_lines[:MAX_LINES])
                    + "```"
                    + " [...] see output at "
                    + url
                )
            else:
                return quote_it(to_print)
    except Exception as e:
        print(e)
        url = web.paste(data=str(resp).encode("utf-8"))
        return "No output. Maybe something bad happened - see " + url
