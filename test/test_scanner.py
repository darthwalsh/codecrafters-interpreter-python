import unittest

from app.scanner import Scanner, Token, TokenType as T

# See https://github.com/munificent/craftinginterpreters/tree/01e6f5b8f3e5dfa65674c2f9cf4700d73ab41cf8/test/scanning

class TestScanner(unittest.TestCase):
    def validate(self, source, *types):
        scanner = Scanner(source)
        tokens = scanner.scan_tokens()
        self.assertSequenceEqual(
            [t.type if isinstance(t, Token) else "ERR" for t in tokens], types + (T.EOF,)
        )

    def lit(self, source, expected):
        it = Scanner(source).scan_tokens()
        self.assertEqual(next(it).literal, expected)
        self.assertEqual(next(it).type, T.EOF)

    def test_eof(self):
        self.validate("")
        self.validate("//message")
        self.validate("//message\n")

    def test_ops(self):
        self.validate("! = !=", T.BANG, T.EQUAL, T.BANG_EQUAL)

    def test_keyword(self):
        self.validate("var true", T.VAR, T.TRUE)

    def test_identifier(self):
        self.validate("_", T.IDENTIFIER)
        self.validate("A1_", T.IDENTIFIER)

    def test_number(self):
        self.validate("1 12 123 12.3", T.NUMBER, T.NUMBER, T.NUMBER, T.NUMBER)
        self.lit("1", 1.0)
        self.lit("123", 123.0)
        self.lit("12.3", 12.3)

        # Not sure on these semantics, but seems to be what the book does.
        self.validate("12.", T.NUMBER, T.DOT)
        self.validate("12. ", T.NUMBER, T.DOT)
        self.validate("12 .", T.NUMBER, T.DOT)
        self.validate("12.a", T.NUMBER, T.DOT, T.IDENTIFIER)
        self.validate("12. a", T.NUMBER, T.DOT, T.IDENTIFIER)
        self.validate("12 .a", T.NUMBER, T.DOT, T.IDENTIFIER)
        self.validate(".12", T.DOT, T.NUMBER)

    def test_string(self):
        self.validate('"abc"', T.STRING)
        self.lit('"abc"', "abc")

        self.validate('"abc', "ERR")
        self.validate('"', "ERR")

    def test_error(self):
        self.validate("1 $", T.NUMBER, "ERR")
