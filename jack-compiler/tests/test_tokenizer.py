from __future__ import annotations

import unittest

from jackc.errors import JackError
from jackc.tokenizer import TokenKind, tokenize


class TokenizerTests(unittest.TestCase):
    def test_basic_tokens(self) -> None:
        tokens = tokenize('class Main { function void main() { return; } }')
        self.assertEqual(
            [(token.kind, token.text) for token in tokens],
            [
                (TokenKind.KEYWORD, "class"),
                (TokenKind.IDENTIFIER, "Main"),
                (TokenKind.SYMBOL, "{"),
                (TokenKind.KEYWORD, "function"),
                (TokenKind.KEYWORD, "void"),
                (TokenKind.IDENTIFIER, "main"),
                (TokenKind.SYMBOL, "("),
                (TokenKind.SYMBOL, ")"),
                (TokenKind.SYMBOL, "{"),
                (TokenKind.KEYWORD, "return"),
                (TokenKind.SYMBOL, ";"),
                (TokenKind.SYMBOL, "}"),
                (TokenKind.SYMBOL, "}"),
            ],
        )

    def test_comments_are_ignored(self) -> None:
        source = """
        // line comment
        class Main { /* block
        comment */ function void main() { return; } }
        """
        tokens = tokenize(source)
        self.assertEqual(tokens[0].kind, TokenKind.KEYWORD)
        self.assertEqual(tokens[0].text, "class")
        self.assertEqual(tokens[1].text, "Main")
        self.assertEqual(len(tokens), 13)

    def test_doc_comment_is_a_block_comment(self) -> None:
        tokens = tokenize("/** A doc comment. */ class Main {}")
        self.assertEqual([token.text for token in tokens], ["class", "Main", "{", "}"])

    def test_string_constant_keeps_spaces_and_escapes(self) -> None:
        tokens = tokenize(r'"HOW MANY NUMBERS? " "a\nb\"c"')
        self.assertEqual(tokens[0].kind, TokenKind.STRING_CONSTANT)
        self.assertEqual(tokens[0].text, "HOW MANY NUMBERS? ")
        self.assertEqual(tokens[1].text, r'a\nb\"c')

    def test_integer_constant_range(self) -> None:
        self.assertEqual(tokenize("32767")[0].text, "32767")
        with self.assertRaises(JackError):
            tokenize("32768")

    def test_identifier_rules(self) -> None:
        tokens = tokenize("_x9 Abc_123")
        self.assertEqual([token.kind for token in tokens], [TokenKind.IDENTIFIER] * 2)
        self.assertEqual([token.text for token in tokens], ["_x9", "Abc_123"])

    def test_symbols_are_single_tokens(self) -> None:
        symbols = "{}()[].,;+-*/&|<>=~"
        tokens = tokenize(symbols)
        self.assertEqual([token.text for token in tokens], list(symbols))

    def test_unterminated_block_comment(self) -> None:
        with self.assertRaisesRegex(JackError, "unterminated block comment"):
            tokenize("class Main { /* oops")

    def test_unterminated_string(self) -> None:
        with self.assertRaisesRegex(JackError, "unterminated string constant"):
            tokenize('class Main { let s = "oops; }')

    def test_string_cannot_span_lines(self) -> None:
        with self.assertRaisesRegex(JackError, "may not span lines"):
            tokenize('"hello\nworld"')

    def test_unexpected_character(self) -> None:
        with self.assertRaisesRegex(JackError, "unexpected character"):
            tokenize("class Main { @ }")

    def test_error_includes_location(self) -> None:
        with self.assertRaises(JackError) as context:
            tokenize("class Main {\n  @\n}", filename="Main.jack")
        self.assertEqual(context.exception.filename, "Main.jack")
        self.assertEqual(context.exception.line, 2)
        self.assertEqual(context.exception.column, 3)


if __name__ == "__main__":
    unittest.main()
