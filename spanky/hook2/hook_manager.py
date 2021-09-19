# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations

from .hook2 import Hook
from .actions import ActionOnReady, ActionEvent
from .event import EventType
import os
import glob
from types import ModuleType, CoroutineType
import importlib
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spanky.bot import Bot

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
        self.plugin_hook = Hook(f"plugin_obj_{path!s}")

    # load actually imports the plugin and returns wether to continue with the module loading:
    # NOTE: This maybe can be done in a better way, try and find it.
    async def load(self) -> bool:

        # Load module
        print(f"Loading {self.name}")
        name = self.name.replace("/", ".").replace(".py", "")

        try:
            self.module = importlib.import_module(name)
            if self.module in modules:
                self.module = importlib.reload(self.module)
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
        for hook in self.hooks:
            # print(hook.hook_id)
            self.plugin_hook.add_child(hook)
            tasks.append(
                asyncio.create_task(
                    hook.dispatch_action(
                        ActionEvent(self.mgr.bot, {}, EventType.on_start)
                    )
                )
            )

            # Run on ready work
            if self.mgr.bot.is_ready:
                for server in self.mgr.bot.get_servers():
                    tasks.append(
                        asyncio.create_task(
                            hook.dispatch_action(ActionOnReady(self.mgr.bot, server))
                        )
                    )
                tasks.append(
                    asyncio.create_task(
                        hook.dispatch_action(
                            ActionEvent(self.mgr.bot, {}, EventType.on_conn_ready)
                        )
                    )
                )
        await asyncio.gather(*tasks)

    # unload removes the hooks from the master hook
    def unload(self):
        self.plugin_hook.unload()
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
        return vals


# Watchdog event handler


class PluginDirectory:
    def __init__(self, path: str, mgr: HookManager):
        self.path: str = path
        self.mgr: PluginManager = mgr
        self.plugins: dict[str, Plugin] = {}
        self.observer: Observer = Observer()
        self.event_handler = PluginDirectoryEventHandler(self, patterns=["*.py"])
        self.observer.schedule(self.event_handler, path, recursive=False)
        self.observer.start()

        self.hook = Hook(f"plugin_dir_{path}")
        self.mgr.hook.add_child(self.hook)

        self.reloading = set()

    async def load(self):
        for plugin_file in glob.iglob(os.path.join(self.path, "*.py")):
            plugin = Plugin(plugin_file, self.mgr, self.hook)
            if await plugin.load():
                self.plugins[plugin_file] = plugin

    def unload(self, path):
        if path in self.plugins:
            self.plugins[path].unload()
        pass

    async def reload(self, path):
        # Might have been very quickly deleted
        if not os.path.isfile(path):
            return
        if path in self.reloading:
            return
        self.reloading.add(path)
        print(path)
        await self.plugins[path].reload()
        self.reloading.remove(path)


class PluginDirectoryEventHandler:
    def __init__(self, pd: PluginDirectory, *args, **kwargs):
        self.pd = pd

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
        asyncio.run_coroutine_threadsafe(func(event), self.pd.mgr.bot.loop)

    async def on_created(self, event):
        print("create")
        await self.pd.reload(event.src_path)

    async def on_deleted(self, event):
        print("delete")
        self.pd.unload(event.src_path)

    async def on_modified(self, event):
        print("modify")
        await self.pd.reload(event.src_path)

    async def on_moved(self, event):
        print("move")
        if event.dest_path.endswith(
            ".py" if isinstance(event.dest_path, str) else b".py"
        ):
            self.pd.unload(event.src_path)
            await self.pd.reload(event.dest_path)
