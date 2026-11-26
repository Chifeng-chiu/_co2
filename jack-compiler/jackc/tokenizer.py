"""Tokenizer for the Jack language (nand2tetris project 10).

The tokenizer follows the lexical rules in *The Elements of Computing
Systems*:

* whitespace and comments (``//`` and ``/* ... */``) are ignored;
* keywords, symbols, integer constants, string constants and identifiers are
  the five token classes;
* identifiers start with a letter or underscore and contain letters, digits
  and underscores;
* integer constants must be in the range 0..32767;
* string constants are enclosed in double quotes and may not span lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import JackError


class TokenKind(str, Enum):
    KEYWORD = "keyword"
    SYMBOL = "symbol"
    INTEGER_CONSTANT = "integerConstant"
    STRING_CONSTANT = "stringConstant"
    IDENTIFIER = "identifier"


KEYWORDS = frozenset(
    {
        "class",
        "constructor",
        "function",
        "method",
        "field",
        "static",
        "var",
        "int",
        "char",
        "boolean",
        "void",
        "true",
        "false",
        "null",
        "this",
        "let",
        "do",
        "if",
        "else",
        "while",
        "return",
    }
)

SYMBOLS = frozenset("{}()[].,;+-*/&|<>=~")

MAX_INT = 32767


@dataclass(frozen=True)
class Token:
    """A single Jack token."""

    kind: TokenKind
    text: str
    line: int
    column: int

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        return f"{self.kind.value} {self.text!r} ({self.line}:{self.column})"


class _Scanner:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.filename = filename
        self.length = len(source)
        self.pos = 0
        self.line = 1
        self.column = 1

    def error(self, message: str, line: int | None = None, column: int | None = None) -> JackError:
        return JackError(
            message,
            filename=self.filename,
            line=self.line if line is None else line,
            column=self.column if column is None else column,
        )

    def peek(self, offset: int = 0) -> str:
        index = self.pos + offset
        if index >= self.length:
            return ""
        return self.source[index]

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def skip_trivia(self) -> None:
        while self.pos < self.length:
            ch = self.peek()
            if ch in " \t\r\n\f\v":
                self.advance()
                continue
            if ch == "/" and self.peek(1) == "/":
                self.advance()
                self.advance()
                while self.pos < self.length and self.peek() != "\n":
                    self.advance()
                continue
            if ch == "/" and self.peek(1) == "*":
                start_line, start_column = self.line, self.column
                self.advance()
                self.advance()
                closed = False
                while self.pos < self.length:
                    if self.peek() == "*" and self.peek(1) == "/":
                        self.advance()
                        self.advance()
                        closed = True
                        break
                    self.advance()
                if not closed:
                    raise self.error(
                        "unterminated block comment",
                        line=start_line,
                        column=start_column,
                    )
                continue
            break

    def scan(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self.skip_trivia()
            if self.pos >= self.length:
                return tokens

            line, column = self.line, self.column
            ch = self.peek()

            if ch == '"':
                tokens.append(self.scan_string(line, column))
                continue

            if ch in "0123456789":
                tokens.append(self.scan_integer(line, column))
                continue

            if (ch.isascii() and ch.isalpha()) or ch == "_":
                tokens.append(self.scan_identifier(line, column))
                continue

            if ch in SYMBOLS:
                self.advance()
                tokens.append(Token(TokenKind.SYMBOL, ch, line, column))
                continue

            raise self.error(f"unexpected character {ch!r}", line, column)

    def scan_string(self, line: int, column: int) -> Token:
        self.advance()  # opening quote
        chars: list[str] = []
        while True:
            if self.pos >= self.length:
                raise self.error("unterminated string constant", line, column)
            ch = self.peek()
            if ch == "\n" or ch == "\r":
                raise self.error("string constant may not span lines", line, column)
            if ch == '"':
                self.advance()
                return Token(TokenKind.STRING_CONSTANT, "".join(chars), line, column)
            if ch == "\\":
                # Keep escape sequences in the token text.  The XML output
                # shows them exactly as written, while the code generator
                # decodes them (the official compiler supports escapes such
                # as \n, \t, \\, \" and \]).
                chars.append(self.advance())
                if self.pos >= self.length:
                    raise self.error("unterminated string constant", line, column)
                escaped = self.peek()
                if escaped == "\n" or escaped == "\r":
                    raise self.error("string constant may not span lines", line, column)
                chars.append(self.advance())
                continue
            chars.append(self.advance())

    def scan_integer(self, line: int, column: int) -> Token:
        digits: list[str] = []
        while self.pos < self.length and self.peek() in "0123456789":
            digits.append(self.advance())
        text = "".join(digits)
        value = int(text)
        if value > MAX_INT:
            raise self.error(
                f"integer constant {text} is outside the range 0..{MAX_INT}",
                line,
                column,
            )
        return Token(TokenKind.INTEGER_CONSTANT, text, line, column)

    def scan_identifier(self, line: int, column: int) -> Token:
        chars: list[str] = []
        while self.pos < self.length:
            ch = self.peek()
            if (ch.isascii() and ch.isalnum()) or ch == "_":
                chars.append(self.advance())
            else:
                break
        text = "".join(chars)
        kind = TokenKind.KEYWORD if text in KEYWORDS else TokenKind.IDENTIFIER
        return Token(kind, text, line, column)


def tokenize(source: str, filename: str = "<input>") -> list[Token]:
    """Return the list of Jack tokens in *source*.

    Raises :class:`jackc.errors.JackError` for lexical errors.
    """

    return _Scanner(source, filename).scan()
