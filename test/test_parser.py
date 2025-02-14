import unittest

from app.ast import AstPrinter
from test.runner import parse, errors, parse_expr, parse_stmt, reraise


class TestParser(unittest.TestCase):
    def validate(self, source, printed):
        expr = parse(source, reraise)
        self.assertEqual(AstPrinter().print(expr), printed)

    def error(self, source, error: str, parsed: str | None):
        e = parse_stmt(source) if ";" in source or "{" in source else parse_expr(source)
        self.assertEqual(errors, [error])

        if parsed is None:
            self.assertIsNone(e)
        else:
            self.assertEqual(AstPrinter().print(e), parsed)

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

    def test_assign(self):
        self.validate("x = y", "(= x y)")
        self.validate("x = y = z", "(= x (= y z))")

        self.error("x =", "Expect expression", None)
        self.error("1 = x", "Invalid assignment target.", "1.0")

    def test_var(self):
        self.validate("var x = 1 + x;", "var x = (+ 1.0 x);")

    def test_print(self):
        self.validate("print 1;", "print 1.0;")
        
        self.error("print 1; 3", "Expect ';' after expression.", "print 1.0;")
        self.error("print; 3;", "Expect expression", "3.0;")

    def test_block(self):
        self.validate("{1;}", "{ 1.0; }")
        self.validate("{}", "{  }")
        self.validate("{1;}{}", "{ 1.0; } {  }")

        self.error("{", "Expect '}' after block.", "")

    def test_trailing(self):
        self.error("1 1", "Expected end of expression", "1.0")

    def test_trailing_after_parens(self):
        self.error("(72 +)", "Expect expression", None)
