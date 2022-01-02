from . import arg_parser


class SArg:
    """
    Slash command container
    """

    def __init__(
        self,
        name: str = None,
        stype=None,
        description: str = None,
        choices: list = [],
        default=None,
    ):

        self.name = name
        # TODO handle channel type
        self.type = stype
        self.description = description
        self.choices = choices
        self.default = default

    @classmethod
    def from_parser(cls, values):
        """
        Build a slash argument given a parser object.
        """
        obj = cls()

        obj.name = values[arg_parser.PName.name]

        if arg_parser.PArgType.name in values:
            obj.type = values[arg_parser.PArgType.name]

        if arg_parser.PChoice.name in values:
            obj.set_choices(values[arg_parser.PChoice.name])

        if arg_parser.PDescription.name in values:
            obj.description = values[arg_parser.PDescription.name]

        if arg_parser.PDefaultVal.name in values:
            obj.default = values[arg_parser.PDefaultVal.name]

        return obj

    def set_choices(self, choices: list):
        """
        Prepares the choices dict.
        """
        dict_choices = {}
        for choice in choices:
            dict_choices[str(choice)] = choice

        self.choices = dict_choices
