from spanky.plugin import hook

@hook.command
async def mock(text, event, str_to_id, reply):
    """<nick> - turn <user>'s last message in to aLtErNaTiNg cApS"""
    nick = str_to_id(text.strip())
    try:
        lines = await event.channel.async_get_latest_messages(100)
    
        line = None
        for msg in lines[::-1]:
            if msg.author.id == nick:
                line = msg.text
                
        if line is None:
            reply("Nothing found in recent history for {}".format(nick))
            return 
    
        # Return the message in aLtErNaTiNg cApS
        line = "".join(c.upper() if i & 1 else c.lower() for i, c in enumerate(line))
        reply(line)
    except Exception as e:
        print(e)
