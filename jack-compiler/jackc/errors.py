"""Error type shared by the tokenizer and parser."""

from __future__ import annotations


class JackError(Exception):
    """A lexical or syntax error with source location information."""

    def __init__(
        self,
        message: str,
        filename: str | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column

    def __str__(self) -> str:
        location = ""
        if self.filename:
            location = self.filename
        if self.line is not None:
            location += f":{self.line}"
            if self.column is not None:
                location += f":{self.column}"
        if location:
            return f"{location}: {self.message}"
        return self.message
