import unittest

from app.interpreter import Interpreter
from app.scanner import Scanner
from app.parser import AstPrinter, Parser


errors = []


def report(_line, _where, message):
    errors.append(message)


class TestScanner(unittest.TestCase):
    def evaluate(self, source):
        errors.clear()
        tokens = Scanner(source, report).scan_tokens()
        expr = Parser(tokens, report).parse()
        interpreter = Interpreter()
        return interpreter.stringify(interpreter.evaluate(expr))

    def validate(self, source, expected):
        o = self.evaluate(source)
        self.assertEqual(errors, [])
        self.assertEqual(o, expected)

    def test_literal(self):
        self.validate("1", "1")
        self.validate("0.234", "0.234")
        self.validate('"ab"', "ab")
        self.validate("true", "true")
        self.validate("nil", "nil")

    def test_grouping(self):
        self.validate("(1)", "1")
        self.validate("((1))", "1")

    def test_unary(self):
        self.validate("-73", "-73")
        self.validate("--12", "12")
        self.validate("!true", "false")
        self.validate("!(!true)", "true")
        
        self.validate("!nil", "true")
        self.validate("!0", "true")
        self.validate('!""', "false")
        self.validate('!"A"', "false")

        # TODO error cases
