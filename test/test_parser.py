import unittest

from app.scanner import Scanner
from app.parser import AstPrinter, Parser

class TestScanner(unittest.TestCase):
    def validate(self, source, printed):
        tokens = Scanner(source).scan_tokens()
        expr = Parser(tokens).parse()

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
        tokens = Scanner("1 1").scan_tokens()
        parser = Parser(tokens)
        e = parser.parse()

        self.assertTrue(parser.has_error)
        self.assertEqual(AstPrinter().print(e), "1.0")
