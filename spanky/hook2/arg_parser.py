from dataclasses import dataclass, field
from io import BytesIO
from token import NUMBER, OP, NAME, STRING, ENCODING, NEWLINE, ENDMARKER
from tokenize import tokenize, TokenError

MAGIC_START = ":sarg"


@dataclass
class PTok:
    """
    Generic token class for handling types.
    """

    valid_type: list  # What values are valid - taken from token.*
    next_state: list  # What the next state should be
    start: str = None  # Marks start of type
    end: str = None  # Marks end of type
    delimiter: str = None  # type delimiter

    is_done: bool = False  # type has been filled

    # Accumulate values
    _accumulator: list = field(default_factory=list)

    def is_valid(self, tok_type, value):
        """
        Checks whether the given token is valid for the current type.

        Returns True if any of the following: the token type is the valid type or the token marks a 'start' or 'end'.
        False otherwise.

        Returning True signals that the token has been consumed.
        """
        is_valid = False
        to_append = value

        if self.marks_start(tok_type, value):
            is_valid = True
            to_append = self.start

        elif tok_type in self.valid_type:

            # If there's no end marker, mark it as done here
            if self.end is None:
                self.is_done = True

            is_valid = True

        elif self.delimiter and self.delimiter.is_delim(tok_type, value):
            is_valid = True
            to_append = self.delimiter

        elif self.end and self.end.is_delim(tok_type, value):
            self.is_done = True
            is_valid = True
            to_append = self.end

        if is_valid:
            self._accumulator.append(to_append)

        return is_valid

    def marks_start(self, tok_type, value):
        """
        Checks whether the given token marks the start of the type.
        """
        if self.start and self.start.is_delim(tok_type, value):
            return True

        return False

    def is_type(self, tok_type):
        """ "
        Checks whether the given token is a valid type for this type.
        """
        return tok_type in self.valid_type

    def should_advance(self, tok_type, value):
        """
        Cycles through potential next states and returns the next state instance if found.

        The next state is returned when the next type start has been identified OR
        the token is of the given type. The second statement is needed because some
        types may not have a start delimiter.
        """
        for next in self.next_state:
            next_inst = next()
            if next_inst.marks_start(tok_type, value) or next_inst.is_type(tok_type):
                return next_inst

        return None

    def get_content(self):
        """
        Return the raw acumulator.
        """
        return self._accumulator

    def get_content_no_delim(self):
        """
        Return the acumulator without delimiters.
        """
        return [i for i in self._accumulator if type(i) != PDel]

    def validate(self):
        return self.get_content_no_delim()

    # Removes quotes around strings
    def validate_str(self, data):
        if data.startswith("'"):
            data = data[1:]

        if data.endswith("'"):
            data = data[:-1]

        return str(data)


@dataclass
class PDel:
    """
    Basic delimiter container that holds a token type and a value.
    """

    valid_type: int
    value: str = ""

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value

    def __eq__(self, __o: object) -> bool:
        if type(__o) == str and __o == self.value:
            return True

        return False

    def is_delim(self, type, value):
        """
        Checks if the token is this delimiter type.
        """
        if self.valid_type == type and self.value == value:
            return True

        return False


class PStart(PTok):
    name = "start"

    def __init__(self):
        super().__init__(valid_type=[ENCODING], next_state=[PName])


class PName(PTok):
    name = "name"

    def __init__(self):
        super().__init__(
            valid_type=[NAME],
            next_state=[PChoice, PArgType, PDefaultVal, PDescription, PEnd],
        )

    def validate(self):
        return str(self._accumulator[0])


class PChoice(PTok):
    name = "choice"

    def __init__(self):
        super().__init__(
            valid_type=[NUMBER, STRING, NAME],
            next_state=[PArgType, PDefaultVal, PDescription, PEnd],
            start=PDel(OP, "["),
            end=PDel(OP, "]"),
            delimiter=PDel(OP, ","),
        )

    def validate(self, argtype) -> list:
        if argtype == str:
            return [argtype(self.validate_str(i)) for i in self.get_content_no_delim()]

        return [argtype(i) for i in self.get_content_no_delim()]


class PArgType(PTok):
    name = "arg_type"

    def __init__(self):
        super().__init__(
            valid_type=[NAME],
            next_state=[PDefaultVal, PDescription, PEnd],
            start=PDel(OP, ":"),
        )

    def validate(self):
        tok_type = self.get_content_no_delim()[0]

        if tok_type == "str":
            return str

        elif tok_type == "int":
            return int

        elif tok_type == "float":
            return float

        elif tok_type == "chan":
            return "chan"

        else:
            raise ValueError(f"Unhandled type {tok_type}")


class PDefaultVal(PTok):
    name = "default_value"

    def __init__(self):
        super().__init__(
            valid_type=[NUMBER, STRING, NAME],
            next_state=[PDescription, PEnd],
            start=PDel(OP, "="),
            delimiter=PDel(OP, "-"),
        )

    def validate(self, argtype) -> list:
        if argtype == str:
            return argtype(self.validate_str(self.get_content_no_delim()[0]))

        return argtype(self.get_content_no_delim()[0])


class PDescription(PTok):
    name = "description"

    def __init__(self):
        super().__init__(
            valid_type=[NAME, STRING], next_state=[PEnd], start=PDel(OP, "|")
        )

    def validate(self):
        return " ".join(self.get_content_no_delim())


class PEnd(PTok):
    name = "end"

    def __init__(self):
        super().__init__(valid_type=[ENDMARKER, NEWLINE], next_state=[])


class Parser:
    """
    Parses a token list and returns the result.

    Initialized using a token list that is consumed from index 0.
    """

    def __init__(self, tokens) -> None:
        self._results = []
        self.current = PStart()
        self._tokens = tokens

    @property
    def current(self):
        return self._crt_state

    @current.setter
    def current(self, value):
        self._crt_state = value
        self._results.append(value)

    def consume_token(self):
        """
        Pops the first token.
        """
        if len(self._tokens) == 0:
            return None

        return self._tokens.pop(0)

    def push_token(self, token):
        """
        Pushes a token back onto the stack.
        """
        self._tokens.insert(0, token)

    def has_tokens(self):
        return len(self._tokens) != 0

    def process(self):
        """
        Process the token queue until it's exhausted.
        """
        while self.has_tokens():
            # Consume a token
            # Should never return None because the while loop guards for that
            tok_type, value, _, _, _ = token = self.consume_token()

            # If the current token is valid, then it's been consumed
            if self.current.is_valid(tok_type, value):
                continue
            else:
                # Invalid tokens are pushed back
                self.push_token(token)

            # Check if we should advance to the next state
            if self.current.is_done:
                next_state = self.current.should_advance(tok_type, value)
                if next_state:
                    self.current = next_state
                    continue

            # Raise an exception as the parser should never mishandle a type
            raise ValueError(f"Unhandled token {value} of type {tok_type}")

    def get_results(self):
        results = {}
        for val in self._results:
            results[val.name] = val

        return results

    def is_done(self):
        return type(self.current) == PEnd

    def validate(self):
        """
        Extract the validated results.
        """
        if not self.is_done():
            raise ValueError("Parser is not done.")

        results = self.get_results()

        if PArgType.name in results:
            results[PArgType.name] = results[PArgType.name].validate()
        else:
            # Implicit type is str
            results[PArgType.name] = str

        if PName.name not in results:
            raise ValueError("Missing variable name.")

        results[PName.name] = results[PName.name].validate()

        if PChoice.name in results:
            results[PChoice.name] = results[PChoice.name].validate(
                results[PArgType.name]
            )

        if PDefaultVal.name in results:
            results[PDefaultVal.name] = results[PDefaultVal.name].validate(
                results[PArgType.name]
            )

        if PDescription.name in results:
            results[PDescription.name] = results[PDescription.name].validate()

        return results


def parse(data, magic_start=MAGIC_START) -> dict:
    """
    Parse a line and return the results in a dict that contains
    parsed and validated values.
    """
    states = []
    for line in data.split("\n"):
        line = line.strip()

        if not line.startswith(magic_start):
            continue

        line = line.replace(magic_start, "")

        parsed = tokenize(BytesIO(line.strip().encode("utf-8")).readline)

        tokens = list(parsed)

        state = Parser(tokens)
        state.process()
        states.append(state)

    return states
