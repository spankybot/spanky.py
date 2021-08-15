# Delay checking for typing (TODO: remove when bot runs on python 3.10)
from __future__ import annotations

from .hook2 import Hook, ActionOnReady, ActionEvent
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

class HookManager():
    def __init__(self, paths: list[str], bot: Bot):
        self.bot: Bot = bot
        self.paths: list[str] = paths
        self.hook: Hook = self.bot.hook2
        self.directories: dict[str, PluginDirectory] = {}
        for path in paths:
            self.directories[path] = PluginDirectory(path, self)

class Plugin():
    def __init__(self, path: str, mgr: PluginManager):
        self.name: str = path
        self.module: Optional[ModuleType] = None
        self.mgr: PluginManager = mgr
        self.loaded: bool = False

    # load actually imports the plugin and returns wether to continue with the module loading:
    # NOTE: This maybe can be done in a better way, try and find it.
    def load(self) -> bool:
        
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
        print(f"Found {len(self.hooks)} Hook2s in plugin {self.name}")
        self.finalize_hooks()

        self.loaded = True

        return True
    
    # finalize_hooks fires on_start and (if the bot is already loaded) on_ready and on_conn_ready events to the hooks
    def finalize_hooks(self):
        for hook in self.hooks:
            print(hook.hook_id)
            self.mgr.hook.add_child(hook)
            self.mgr.bot.run_sync(hook.dispatch_action(ActionEvent(self.mgr.bot, {}, EventType.on_start)))
            
            # Run on ready work
            if self.mgr.bot.is_ready:
                for server in self.mgr.bot.get_servers():
                    self.mgr.bot.run_sync(hook.dispatch_action(ActionOnReady(self.mgr.bot, server)))
                self.mgr.bot.run_sync(hook.dispatch_action(ActionEvent(self.mgr.bot, {}, EventType.on_conn_ready)))

    # unload removes the hooks from the master hook
    def unload(self):
        for hook in self.hooks:
            hook.unload()
        self.loaded = False
        print(f"Unloaded {self.name}")

    # reload is shorthand for unloading then loading
    def reload(self) -> bool:
        self.unload()
        return self.load()

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

class PluginDirectory():
    def __init__(self, path: str, mgr: HookManager):
        self.path: str = path
        self.mgr: PluginManager = mgr
        self.plugins: dict[str, Plugin] = {}
        self.observer: Observer = Observer()
        self.event_handler = PluginDirectoryEventHandler(self, patterns=["*.py"])
        self.observer.schedule(self.event_handler, path, recursive=False)
        self.observer.start()

        self.reloading = set() 

        # Initially load all plugins
        self.load()

    def load(self):
        for plugin_file in glob.iglob(os.path.join(self.path, '*.py')):
            plugin = Plugin(plugin_file, self.mgr)
            if plugin.load():
                self.plugins[plugin_file] = plugin

    def unload(self, path):
        if path in self.plugins:
            self.plugins[path].unload()
        pass

    def reload(self, path):
        # Might have been very quickly deleted
        if not os.path.isfile(path):
            return
        if path in self.reloading:
            return
        self.reloading.add(path)
        print(path)
        self.plugins[path].reload()
        self.reloading.remove(path)

class PluginDirectoryEventHandler(PatternMatchingEventHandler):
    def __init__(self, pd: PluginDirectory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pd = pd

    def on_created(self, event):
        print("create")
        self.pd.reload(event.src_path)

    def on_deleted(self, event):
        print("delete")
        self.pd.unload(event.src_path)

    def on_modified(self, event):
        print("modify")
        self.pd.reload(event.src_path)

    def on_moved(self, event):
        print("move")
        if event.dest_path.endswith('.py' if isinstance(event.dest_path, str) else b".py"):
            self.pd.unload(event.src_path)
            self.pd.reload(event.dest_path)
