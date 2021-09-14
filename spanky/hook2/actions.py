from .event import EventType

class Action:
    """Action is the base class for an action"""
    def __init__(self, event_type: EventType, bot, event):
        self.bot = bot
        self.event_type = event_type
        self._raw = event
        self.context = {}

        self.server_id: Optional[str] = None
        if hasattr(event, "server_id"):
            self.server_id = event.server_id
        if hasattr(event, "server"):
            self.server_id = event.server.id

    def __str__(self):
        return f"Action[{self.event_type=!s} {self.server_id=}]"

class ActionCommand(Action):
    def __init__(self, bot, event, text: str, command: str):
        super().__init__(EventType.command, bot, event)
        self.text: str = text
        self.triggered_command: str = command
        self.author = event.author
        self.channel = event.channel

        self.is_pm = event.is_pm

    def reply(self, text, **kwargs):
        self._raw.reply(text, **kwargs)
        

class ActionPeriodic(Action):
    def __init__(self, bot, target):
        super().__init__(EventType.periodic, bot, {})
        self.target = target

class ActionEvent(Action):
    def __init__(self, bot, event, event_type):
        super().__init__(event_type, bot, event)

class ActionOnReady(Action):
    def __init__(self, bot, server):
        super().__init__(EventType.on_ready, bot, {})
        self.server = server

