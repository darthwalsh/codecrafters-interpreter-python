import unittest

from app.ast import AstPrinter
from test.runner import parse, errors, parse_expr, parse_stmt


class TestParser(unittest.TestCase):
    def validate(self, source, printed):
        expr = parse(source)
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

    def test_expression(self):
        self.validate("1;", "1.0;")

    def test_print(self):
        self.validate("print 1;", "print 1.0;")
        
        e = parse_stmt("print 1; 3")
        self.assertEqual(errors, ["Expect ';' after expression."])
        self.assertEqual(AstPrinter().print(e), "print 1.0;")

    def test_trailing(self):
        e = parse_expr("1 1")

        self.assertEqual(errors, ["Expected end of expression"])
        self.assertEqual(AstPrinter().print(e), "1.0")

    def test_trailing_after_parens(self):
        e = parse_expr("(72 +)")

        self.assertEqual(errors, ["Expect expression"])
        self.assertIsNone(e)
