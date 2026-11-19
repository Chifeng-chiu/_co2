"""Parser for the Nand2Tetris VM language (Chapters 7 and 8)."""


class Parser:
    """Read a .vm file and provide access to its commands one at a time."""

    C_ARITHMETIC = "C_ARITHMETIC"
    C_PUSH = "C_PUSH"
    C_POP = "C_POP"
    C_LABEL = "C_LABEL"
    C_GOTO = "C_GOTO"
    C_IF = "C_IF"
    C_FUNCTION = "C_FUNCTION"
    C_RETURN = "C_RETURN"
    C_CALL = "C_CALL"

    _ARITHMETIC_COMMANDS = {
        "add",
        "sub",
        "neg",
        "eq",
        "gt",
        "lt",
        "and",
        "or",
        "not",
    }

    _COMMAND_TYPES = {
        "push": C_PUSH,
        "pop": C_POP,
        "label": C_LABEL,
        "goto": C_GOTO,
        "if-goto": C_IF,
        "function": C_FUNCTION,
        "return": C_RETURN,
        "call": C_CALL,
    }

    def __init__(self, file_name):
        self._commands = []
        self._current_index = -1
        self._current_command = None

        with open(file_name, "r", encoding="utf-8-sig") as vm_file:
            for raw_line in vm_file:
                # Remove comments and surrounding whitespace.
                line = raw_line.split("//", 1)[0].strip()
                if line:
                    self._commands.append(line)

    def has_more_lines(self):
        """Return True when another VM command is available."""
        return self._current_index + 1 < len(self._commands)

    def advance(self):
        """Move to the next VM command."""
        if not self.has_more_lines():
            raise StopIteration("No more VM commands.")
        self._current_index += 1
        self._current_command = self._commands[self._current_index]

    def command_type(self):
        """Return the type of the current VM command."""
        tokens = self._tokens()
        first = tokens[0]

        if first in self._ARITHMETIC_COMMANDS:
            return self.C_ARITHMETIC
        try:
            return self._COMMAND_TYPES[first]
        except KeyError as exc:
            raise ValueError("Unknown VM command: {!r}".format(first)) from exc

    def arg1(self):
        """Return the first argument of the current command.

        For an arithmetic command, the command itself is returned.
        """
        tokens = self._tokens()
        if self.command_type() == self.C_ARITHMETIC:
            return tokens[0]
        if self.command_type() == self.C_RETURN:
            raise ValueError("arg1() is not valid for a return command.")
        if len(tokens) < 2:
            raise ValueError("Missing first argument in command: {!r}".format(self._current_command))
        return tokens[1]

    def arg2(self):
        """Return the second argument of the current command as an int."""
        tokens = self._tokens()
        if len(tokens) < 3:
            raise ValueError("Missing second argument in command: {!r}".format(self._current_command))
        try:
            return int(tokens[2])
        except ValueError as exc:
            raise ValueError("Second argument is not an integer: {!r}".format(tokens[2])) from exc

    def _tokens(self):
        if self._current_command is None:
            raise RuntimeError("advance() must be called before reading a command.")
        return self._current_command.split()
