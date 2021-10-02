from .event import EventType

from spanky.inputs.discord_py import EventPeriodic


class Action:
    """Action is the base class for an action"""

    def __init__(self, event_type: EventType, bot, event):
        self.bot = bot
        self.event_type = event_type
        self._raw = event

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
        self.server = event.server
        self.is_pm = event.is_pm
        self.message = event.msg

        self.context = {}

    def copy(self) -> "ActionCommand":
        act = ActionCommand(self.bot, self._raw, self.text, self.triggered_command)
        act.context = self.context.copy()
        return act

    def reply(self, text, **kwargs):
        self._raw.reply(text, **kwargs)


class ActionPeriodic(Action):
    def __init__(self, bot, target):
        super().__init__(EventType.periodic, bot, EventPeriodic())
        self.target = target


class ActionEvent(Action):
    def __init__(self, bot, event, event_type):
        super().__init__(event_type, bot, event)
