import unittest

from app.ast import AstPrinter
from app.scanner import Scanner
from app.parser import Parser


errors = []


def report(_line, _where, message):
    errors.append(message)


class TestParser(unittest.TestCase):
    def parse(self, source):
        errors.clear()
        tokens = Scanner(source, report).scan_tokens()
        return Parser(tokens, report).parse() if not errors else None

    def validate(self, source, printed):
        expr = self.parse(source)
        self.assertEqual(errors, [])
        self.assertEqual(AstPrinter().print(expr), printed)

    def test_primary(self):
        self.validate("1", "1.0")
        self.validate('"ab"', "ab")
        self.validate("(true)", "(group true)")
        self.validate("((true))", "(group (group true))")

    def test_equality(self):
        self.validate("1 == 1", "(== 1.0 1.0)")
        self.validate("1 == 2 == 3", "(== (== 1.0 2.0) 3.0)")

    def test_term(self):
        self.validate("1 + 2", "(+ 1.0 2.0)")

    def test_factor(self):
        self.validate("1 * 2 + 3", "(+ (* 1.0 2.0) 3.0)")
        self.validate("1 - 2 / 3", "(- 1.0 (/ 2.0 3.0))")

    def test_unary(self):
        self.validate("!1", "(! 1.0)")
        self.validate("!!1", "(! (! 1.0))")

    def test_trailing(self):
        e = self.parse("1 1")

        self.assertEqual(errors, ["Expected end of expression"])
        self.assertEqual(AstPrinter().print(e), "1.0")

    def test_trailing_after_parens(self):
        e = self.parse("(72 +)")

        self.assertEqual(errors, ["Expect expression"])
        self.assertIsNone(e)
