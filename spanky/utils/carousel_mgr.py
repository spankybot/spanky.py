from typing import TYPE_CHECKING, Any, Type, Protocol

import nextcord

from spanky.hook2 import Hook, server_storage
import spanky.utils.carousel as carousel

if TYPE_CHECKING:
    from spanky.bot import Bot
    from spanky.inputs.nextcord import Server


class Serializable(Protocol):
    def serialize(self) -> dict:
        raise Exception("Not implemented")

    @staticmethod
    def deserialize(bot, data) -> Any:
        raise Exception("Not implemented")


class SelectorManager:
    def __init__(self, bot: "Bot", hook: Hook, dkey: str, cls: Type[carousel.Selector]):
        self.bot = bot
        self.hook = hook
        self.dkey = dkey  # Dict key to iterate over
        self.cls = cls

    async def rebuild(self, server: "Server"):
        storage = self.hook.server_storage(server.id)
        if self.dkey in storage:
            for element in list(storage[self.dkey]):
                try:
                    selector = await self.cls.deserialize(self.bot, element, self.hook)
                    if not selector:
                        continue
                    selector: carousel.Selector = selector
                    selector.upgrade_selector()  # Turn into permanent on rebuild
                    pass
                except nextcord.errors.NotFound:
                    storage[self.dkey].remove(element)
                except:
                    import traceback

                    traceback.print_exc()
