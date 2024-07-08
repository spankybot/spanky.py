import requests
import json
from spanky.plugin import hook
import spanky.utils.discord_utils as dutils

OLLAMA_ENDPOINT = None
MODEL = None

def chat(text, msg_history):
    endpoint = "/api/chat"

    # Copy the history
    msg_history = msg_history.copy()
    msg_history.append({
        "role": "user",
        "content": text
    })

    r = requests.post(
        f"{OLLAMA_ENDPOINT}{endpoint}",
        json=
            {
                "model": MODEL,
                "stream": False,
                "messages": msg_history
            }
        )
    return r.text

@hook.on_start()
def load_endpoint(bot):
    print("Loading LLM plugin")
    if not bot:
        return

    if "ollama_server_address" in bot.config:
        global OLLAMA_ENDPOINT
        OLLAMA_ENDPOINT = bot.config["ollama_server_address"]

        print(f"Using LLM server at {OLLAMA_ENDPOINT}")

    if "ollama_models" in bot.config:
        global MODEL
        if "chat" in bot.config["ollama_models"]:
            MODEL = bot.config["ollama_models"]["chat"]
        elif "default" in bot.config["ollama_models"]:
            MODEL = bot.config["ollama_models"]["default"]

        print(f"Using LLM model {MODEL}")

@hook.command()
async def llm(event, text, storage, async_send_message):
    if not OLLAMA_ENDPOINT:
        return "LLM server not configured"

    if not MODEL:
        return "LLM model not configured"

    """Chat with an AI"""
    if "history" not in storage:
        storage["history"] = {}

    if event.author.id not in storage["history"]:
        storage["history"][event.author.id] = []

    msg_history = storage["history"][event.author.id]

    answer = chat(text, msg_history)
    answer_json = json.loads(answer)
    if "message" not in answer_json:
        return "Error in response from LLM server (1)"
        if "content" not in answer_json["message"]:
            return "Error in response from LLM server (2)"

    answer_content = answer_json["message"]["content"]

    msg_history.append({
        "role": "user",
        "content": f"{event.author.name} says: {text}"
    })
    msg_history.append({
        "role": "assistant",
        "content": answer_content
    })

    # Store the history
    storage["history"][event.author.id] = msg_history
    storage.sync()

    em = dutils.prepare_embed(title=f"Chat with LLM", description=answer_content)
    await async_send_message(embed=em)

@hook.command()
def llm_reset(event, reply, storage):
    """Reset the chat history"""
    if "history" in storage:
        del storage["history"]
        storage.sync()
    reply("Done")