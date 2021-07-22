
class CmdParser():
    """
    Command parser for easily parsing arguments.
    """

    class Exception(Exception):
        """
        Parser exception base class.
        """
        pass

    class HelpException(Exception):
        """
        Parser exception class when help is called.
        """
        pass

    class Result():
        """
        A dictionary of results.
        """
        DEFAULT_STR = "__default_value__"

        def __init__(self, default_value):
            self._data = {
                CmdParser.Result.DEFAULT_STR: default_value
            }

        def __setitem__(self, key, value):
            self._data[key] = value

        def __getitem__(self, key):
            return self._data[key]

        def __getattr__(self, key):
            if key in self._data:
                return self._data[key]

            return self._data[CmdParser.Result.DEFAULT_STR]

        def __repr__(self):
            return str(self)

        def __str__(self):
            return str(self._data[CmdParser.Result.DEFAULT_STR])

    def __init__(self,
                 name,
                 description=None,
                 args=[],
                 default=None,
                 required=False,
                 options=[],
                 action=None):
        """
        Creates a command parser.

        :param name: how this parser is called.
        :param description: the description.
        :param args: list of possible arguments.
        :param default: default value for this option.
        :param requred: whether it's required in an args enumeration.
        :param options: what values it can take
            - does not work together with args.
        :param action: function to call when it's parsed.
        """

        if args != [] and options != []:
            raise CmdParser.Exception(
                "Cannot specify both args and options.")

        self.name = name
        self.description = description
        self.default = default
        self.required = required

        # All options are CmdParser types
        self.options = []
        for option in options:
            if type(option) is not CmdParser:
                self.options.append(CmdParser(option))
            else:
                self.options.append(option)

        # TODO Perhaps all args should be CmdParse?
        self.args = args
        self.action = action

    def __repr__(self):
        """
        repr(CmdParser) is its name.
        """
        return str(self.name)

    def __str__(self):
        """
        str(CmdParser) is its name.
        """
        return str(self.name)

    def __hash__(self):
        """
        Since we're hashing this, we need to define hashable.
        """
        return hash(self.name)

    def __eq__(self, other_object):
        if type(other_object) == CmdParser:
            return self.name == other_object.name
        else:
            return self.name == str(other_object)

    def parse(self, text, **kwargs):
        """
        Parses the given text, passing hwargs to any actions set.
        """
        if type(text) != list:
            text = text.split(" ")

        if len(text) > 0 and text[0] == "help":
            raise CmdParser.HelpException(self.help())

        # Initialize the result.
        # If any text is given, take the first parameter, else default value.
        if len(text) > 0:
            result = CmdParser.Result(text[0])
        else:
            result = CmdParser.Result(self.default)

        # Parse usecase where this is args only
        if self.args:
            # Check the number of arguments
            required_args = []
            for arg in self.args:
                if arg.required:
                    required_args.append(arg)

            if len(text) < len(required_args):
                raise CmdParser.Exception(
                    f"Incorrect number of parameter for {self.name}. Parameters: {self.args}")

            # Build result list

            for order, arg in enumerate(self.args):
                # Add default parameter value
                result[arg] = arg.parse(text[order:], **kwargs)

        # Parse usecase where this is options only
        if self.options:
            # Check if it's a valid option
            if len(text) == 0 or text[0] not in self.options:
                raise CmdParser.Exception(
                    f"Incorrect parameter for {self.name}. Valid parameters: {self.options}")

            for option in self.options:
                if text[0] == str(option):
                    result[option] = CmdParser.Result(
                        option.parse(text[1:], **kwargs))

        # Call the action - if anything was set up
        if self.action:
            self.action(text=text, **kwargs)

        return result

    def help(self, prefix=""):
        """
        Format a help string.
        """
        # Initialize the string with name
        help_string = f"{prefix}{self.name}"

        # Set up the prefix for potential recursive calls
        if prefix == "":
            prefix = "\t"
        else:
            prefix *= 2

        # Add description if it has one
        if self.description:
            help_string += f" ({self.description})"

        # Add colon if this is a more complex command
        if self.args or self.options:
            help_string += ": "

        # Describe args
        if self.args:
            help_string += " ".join(map(str, self.args))

            for arg in self.args:
                help_string += "\n" + arg.help(prefix)

        # Describe options
        if self.options:
            help_string += "[" + ("|".join(map(str, self.options))) + "]"

            for option in self.options:
                help_string += "\n" + option.help(prefix)

        return help_string
