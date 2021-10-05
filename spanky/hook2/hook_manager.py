# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations

from .hook2 import Hook
from .actions import ActionEvent
from .event import EventType
from .hooklet import Hooklet
import os
import glob
from types import ModuleType, CoroutineType
import importlib
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spanky.bot import Bot
    from typing import Coroutine

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

modules: list[ModuleType] = []


class HookManager:
    def __init__(self, paths: list[str], bot: Bot):
        self.bot: Bot = bot
        self.paths: list[str] = paths
        self.hook: Hook = self.bot.hook2
        self.directories: dict[str, PluginDirectory] = {}
        for path in paths:
            self.directories[path] = PluginDirectory(path, self)

    async def load(self):
        tasks = []
        for d in self.directories.values():
            tasks.append(asyncio.create_task(d.load(), name="hook_mgr"))
        await asyncio.gather(*tasks)


class Plugin:
    def __init__(self, path: str, mgr: PluginManager, parent_hook: Hook):
        self.name: str = path
        self.module: Optional[ModuleType] = None
        self.mgr: PluginManager = mgr
        self.parent_hook = parent_hook
        self.loaded: bool = False
        self.plugin_hook: Hook = Hook(f"plugin_obj_{path.replace('/', '_')!s}")

        self.legacy_hook: Optional[Hook] = None

    # load actually imports the plugin and returns wether to continue with the module loading:
    # NOTE: This maybe can be done in a better way, try and find it.
    async def load(self) -> bool:

        # Load module
        print(f"Loading {self.name}")
        name = self.name.replace("/", ".").replace(".py", "")
        hk_name = self.name.replace("/", "_").replace(".py", "")

        try:
            self.module = importlib.import_module(name)
            if self.module in modules:
                self.module = importlib.reload(self.module)
            self.legacy_hook = gen_legacy_hook(self.module, hk_name + "_legacy")
            modules.append(self.module)
        except Exception as e:
            import traceback

            print(f"Error loading plugin {self.name!s}\n\t{e!s}")
            traceback.print_exc()
            return False

        # Load hooks
        # print(f"Found {len(self.hooks)} Hook2s in plugin {self.name}")
        self.parent_hook.add_child(self.plugin_hook)
        await self.finalize_hooks()

        self.loaded = True

        return True

    # finalize_hooks fires on_start and (if the bot is already loaded) on_ready and on_conn_ready events to the hooks
    async def finalize_hooks(self):
        tasks = []
        print("Finalizing hooks", self.hooks)
        for hook in self.hooks:
            # print(hook.hook_id)
            self.plugin_hook.add_child(hook)

            tasks.extend(self.finalize_hook(hook))

        if self.legacy_hook:
            tasks.extend(self.finalize_hook(self.legacy_hook))
        await asyncio.gather(*tasks)

    def finalize_hook(self, hook: Hook) -> list[Coroutine]:
        tasks = []
        tasks.append(
            asyncio.create_task(
                hook.dispatch_action(ActionEvent(self.mgr.bot, {}, EventType.on_start))
            )
        )

        # Run on ready work
        if self.mgr.bot.is_ready:
            for server in self.mgr.bot.get_servers():

                class event:
                    def __init__(self, server):
                        self.server = server

                tasks.append(
                    asyncio.create_task(
                        hook.dispatch_action(
                            ActionEvent(self.mgr.bot, event(server), EventType.on_ready)
                        )
                    )
                )
            tasks.append(
                asyncio.create_task(
                    hook.dispatch_action(
                        ActionEvent(self.mgr.bot, {}, EventType.on_conn_ready)
                    )
                )
            )
        return tasks

    # unload removes the hooks from the master hook
    def unload(self):
        if not self.loaded:
            return
        print(f"Unloading plugin {self.name}")
        self.plugin_hook.unload()
        if self.legacy_hook:
            self.legacy_hook.unload()
        self.loaded = False
        print(f"Unloaded {self.name}")

    # reload is shorthand for unloading then loading
    async def reload(self) -> bool:
        self.unload()
        return await self.load()

    @property
    def hooks(self) -> list[Hook]:
        if not self.module:
            return []
        return self._find_hooks()

    def _find_hooks(self) -> list[Hook]:
        vals = []
        for value in self.module.__dict__.values():
            if isinstance(value, Hook):
                vals.append(value)
        if self.legacy_hook:
            vals.append(self.legacy_hook)
        return vals


def gen_legacy_hook(module, name: str):
    hk2 = Hook(name)
    for value in module.__dict__.values():
        if hasattr(value, "__hk1_wrapped"):
            hooklet: Hooklet = getattr(value, "__hk1_hooklet")(hk2)
            key: str = getattr(value, "__hk1_key")
            getattr(hk2, getattr(value, "__hk1_list")).update({key: hooklet})
    return hk2


# Watchdog event handler


class PluginDirectory:
    def __init__(self, path: str, mgr: HookManager):
        self.path: str = path
        self.mgr: PluginManager = mgr
        self.plugins: dict[str, Plugin] = {}
        self.observer: Observer = Observer()

        self.loop = asyncio.get_event_loop()
        self.event_handler = PluginDirectoryEventHandler(
            self, self.loop, patterns=["*.py"]
        )
        self.observer.schedule(self.event_handler, path, recursive=False)
        self.observer.start()

        self._lock = asyncio.Lock(loop=self.loop)

        self.hook = Hook(f"plugin_dir_{path}")
        self.mgr.hook.add_child(self.hook)

    async def load(self):
        tasks = []
        for plugin_file in glob.iglob(os.path.join(self.path, "*.py")):
            tasks.append(asyncio.create_task(self._load_file(plugin_file)))
        await asyncio.gather(*tasks)

    async def _load_file(self, file: str):
        plugin = Plugin(file, self.mgr, self.hook)
        if await plugin.load():
            self.plugins[file] = plugin

    async def unload(self, path: str):
        async with self._lock:
            print("Doing unload")
            if path in self.plugins:
                self.plugins[path].unload()
                self.plugins.pop(path)
            else:
                print("Unloading unknown plugin")

    async def reload(self, path: str):
        async with self._lock:
            print("Doing reload")
            # Might have been very quickly deleted
            if not os.path.isfile(path):
                return
            print(path)
            if path in self.plugins:
                await self.plugins[path].reload()
            else:
                await self._load_file(path)


class PluginDirectoryEventHandler:
    def __init__(
        self, pd: PluginDirectory, loop: asyncio.BaseEventLoop, *args, **kwargs
    ):
        self.pd = pd
        self._loop = loop

    def valid_event(self, event) -> bool:
        if event.is_directory:
            return False
        paths = []
        if hasattr(event, "dest_path"):
            paths.append(os.fsdecode(event.dest_path))
        if event.src_path:
            paths.append(os.fsdecode(event.src_path))
        for p in paths:
            if p.endswith(".py" if isinstance(p, str) else b".py"):
                return True
        return False

    def dispatch(self, event):
        if not self.valid_event(event):
            return
        func = {
            "created": self.on_created,
            "deleted": self.on_deleted,
            "modified": self.on_modified,
            "moved": self.on_moved,
        }[event.event_type]
        asyncio.run_coroutine_threadsafe(func(event), self._loop)

    async def on_created(self, event):
        print("create")
        await self.pd.reload(event.src_path)

    async def on_deleted(self, event):
        print("delete")
        await self.pd.unload(event.src_path)

    async def on_modified(self, event):
        print("modify")
        await self.pd.reload(event.src_path)

    async def on_moved(self, event):
        print("move")
        if event.dest_path.endswith(
            ".py" if isinstance(event.dest_path, str) else b".py"
        ):
            await self.pd.unload(event.src_path)
            await self.pd.reload(event.dest_path)
