import unittest

from app.scanner import Scanner
from app.scanner import TokenType as TT
from test.runner import reraise

# See https://github.com/munificent/craftinginterpreters/tree/01e6f5b8f3e5dfa65674c2f9cf4700d73ab41cf8/test/scanning


class TestScanner(unittest.TestCase):
    def validate(self, source, *types, error=None):
        errors = []

        def report(_line, _where, message):
            errors.append(message)

        tokens = Scanner(source, report).scan_tokens()
        self.assertSequenceEqual([t.type for t in tokens], types + (TT.EOF,))
        self.assertEqual(errors, [error] if error else [])

    def lit(self, source, expected):
        it = iter(Scanner(source, reraise).scan_tokens())
        self.assertEqual(next(it).literal, expected)
        self.assertEqual(next(it).type, TT.EOF)

    def test_eof(self):
        self.validate("")
        self.validate("//message")
        self.validate("//message\n")

    def test_ops(self):
        self.validate("! = !=", TT.BANG, TT.EQUAL, TT.BANG_EQUAL)

    def test_keyword(self):
        self.validate("var true", TT.VAR, TT.TRUE)

    def test_identifier(self):
        self.validate("_", TT.IDENTIFIER)
        self.validate("A1_", TT.IDENTIFIER)

    def test_number(self):
        self.validate("1 12 123 12.3", TT.NUMBER, TT.NUMBER, TT.NUMBER, TT.NUMBER)
        self.lit("1", 1.0)
        self.lit("123", 123.0)
        self.lit("12.3", 12.3)

        # Not sure on these semantics, but seems to be what the book does.
        self.validate("12.", TT.NUMBER, TT.DOT)
        self.validate("12. ", TT.NUMBER, TT.DOT)
        self.validate("12 .", TT.NUMBER, TT.DOT)
        self.validate("12.a", TT.NUMBER, TT.DOT, TT.IDENTIFIER)
        self.validate("12. a", TT.NUMBER, TT.DOT, TT.IDENTIFIER)
        self.validate("12 .a", TT.NUMBER, TT.DOT, TT.IDENTIFIER)
        self.validate(".12", TT.DOT, TT.NUMBER)

    def test_string(self):
        self.validate('"abc"', TT.STRING)
        self.lit('"abc"', "abc")

        self.validate('"abc', error="Unterminated string.")
        self.validate('"', error="Unterminated string.")

    def test_error(self):
        self.validate("1 $", TT.NUMBER, error="Unexpected character: $")
