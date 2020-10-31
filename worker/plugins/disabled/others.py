from core import hook

@hook.command()
async def do_assign(bot):
    try:
        import discord
        client = bot.backend.client

        ro = None
        for s in client.servers:
            if s.name == "r/Romania":
                ro = s
                break

        role = None
        for r in ro.roles:
            if r.name == "Șef de scară":
                role = r
                break

        for m in ro.members:
            has = False
            for urole in m.roles:
                if urole.name == role.name:
                    has = True
                    break

            if has == False:
                print(m)
                await client.add_roles(m, role)
                import time
                time.sleep(0.2)

    except:
        import traceback
        traceback.print_exc()
