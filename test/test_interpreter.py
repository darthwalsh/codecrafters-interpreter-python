import unittest

from app.interpreter import Interpreter, stringify
from app.scanner import Scanner
from app.parser import Parser


errors = []


def report(_line, _where, message):
    errors.append(message)


def runtime_error(e):
    errors.append(str(e))


class TestInterpreter(unittest.TestCase):
    def parse(self, source):
        # MAYBE have helper for these, with global report
        errors.clear()
        tokens = Scanner(source, report).scan_tokens()
        expr = Parser(tokens, report).parse()
        self.assertEqual(errors, [])
        return expr

    def evaluate(self, source):
        expr = self.parse(source)

        def no_error(e):
            raise AssertionError from e

        interpreter = Interpreter(no_error)
        return stringify(interpreter.evaluate(expr))

    def validate(self, source, expected):
        s = self.evaluate(source)
        self.assertEqual(errors, [])
        self.assertEqual(s, expected)

    def validate_error(self, source):
        interpreter = Interpreter(errors.append)
        interpreter.interpret(self.parse(source), None)
        self.assertEqual(len(errors), 1)

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

        self.validate_error("-nil")

        self.validate("!true", "false")
        self.validate("!(!true)", "true")

        self.validate("!nil", "true")
        self.validate("!0", "true")
        self.validate('!""', "false")
        self.validate('!"A"', "false")

    def test_equality(self):
        self.validate("1 == 1", "true")
        self.validate("1 != 1", "false")
        self.validate("0 == nil", "false")
        self.validate("0 != 1 == true", "true")

        self.validate("0/0 == 0/0", "false")

    def test_inequality(self):
        self.validate("1 < 2", "true")
        self.validate("1 < 1", "false")
        self.validate("4 >= 5", "false")

        self.validate_error('"A" < "B"')

    def test_arithmetic(self):
        self.validate("1+2", "3")
        self.validate("1--1", "2")

        self.validate("0.5 * -2", "-1")
        self.validate("1/0 * -1/0", "-inf")
        self.validate("-1/0 * -1/0", "inf")
        self.validate("1/0 * 0", "nan")

        self.validate("1/0", "inf")
        self.validate("-1/0", "-inf")
        self.validate("-(1/0)", "-inf")
        self.validate("0/0", "nan")

        self.validate_error('"A" * 3')

    def test_concat(self):
        self.validate('"A" + "B"', "AB")

        self.validate_error('"A" + 3')
        self.validate_error('3 + "A"')
