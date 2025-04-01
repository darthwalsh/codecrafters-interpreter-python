import unittest

from app.ast import AstPrinter
from test.runner import parse, parse_for_errors


class TestParser(unittest.TestCase):
    def validate(self, source, printed):
        expr = parse(source)
        self.assertEqual(AstPrinter().view(expr), printed)

    def error(self, source, error: str, expected: str | None):
        errors = []

        def report(_token, message):
            errors.append(message)

        e = parse_for_errors(source, report)
        self.assertEqual(errors, [error])

        if expected is None:
            self.assertIsNone(e)
        else:
            if e is None:
                raise AssertionError("Expected expression, got None.")  # pragma: no cover
            self.assertEqual(AstPrinter().view(e), expected)

    def test_primary(self):
        self.validate("1", "1.0")
        self.validate('"ab"', "ab")
        self.validate("(true)", "(group true)")
        self.validate("((true))", "(group (group true))")

    def test_logical(self):
        self.validate("x and y", "(AND x y)")
        self.validate("x or y", "(OR x y)")

        self.validate("x and y or y", "(OR (AND x y) y)")
        self.validate("x or y and z", "(OR x (AND y z))")

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

    def test_call(self):
        self.validate("a()", "a()")
        self.validate('"abc"(x)(y,z)', "abc(x)(y, z)")

        big = f"a({'x, ' * 255}1.0)"
        self.error(big, "Can't have more than 255 arguments.", big)

    def test_expression(self):
        self.validate("1;", "1.0;")

    def test_assign(self):
        self.validate("x = y", "(= x y)")
        self.validate("x = y = z", "(= x (= y z))")

        self.error("x =", "Expect expression.", None)
        self.error("1 = x", "Invalid assignment target.", "1.0")

    def test_var(self):
        self.validate("var x = 1 + x;", "var x = (+ 1.0 x);")

    def test_function(self):
        self.validate("fun foo() { x; }", "fun foo() { x; }")
        self.validate("fun foo(a) {}", "fun foo(a) {  }")
        self.validate("fun foo(a, b) {}", "fun foo(a, b) {  }")

    def test_return(self):
        self.validate("return a;", "return a;")  # MAYBE refactor when both eq: self.round_trip("return a;")
        self.validate("return;", "return;")

    def test_if(self):
        self.validate("if (1) { 1; }", "if (1.0) [{ 1.0; }]")
        self.validate("if (x) y;", "if (x) [y;]")
        self.validate("if (x) y; else z;", "if (x) [y;] else [z;]")

        self.validate("if (x) if (a) b; else z;", "if (x) [if (a) [b;] else [z;]]")

    def test_for_caramelization(self):
        self.validate(
            "for (var i = 0; i < 3; i = i + 1) i;",
            "{ var i = 0.0; while ((< i 3.0)) [{ i; (= i (+ i 1.0)); }] }",
        )
        self.validate(
            "for (; ; ) { print i; }",
            "while (true) [{ print i; }]",
        )
        self.validate(
            "for (x=6; 2; ) if (x) print i;",
            "{ (= x 6.0); while (2.0) [if (x) [print i;]] }",
        )

    def test_while(self):
        self.validate("while (1) 1;", "while (1.0) [1.0;]")
        self.validate("while (1) { 1; }", "while (1.0) [{ 1.0; }]")

    def test_print(self):
        self.validate("print 1;", "print 1.0;")

        self.error("print 1; 3", "Expect ';' after expression.", "print 1.0;")
        self.error("print; 3;", "Expect expression.", "3.0;")

    def test_block(self):
        self.validate("{1;}", "{ 1.0; }")
        self.validate("{}", "{  }")
        self.validate("{1;}{}", "{ 1.0; } {  }")

        self.error("{", "Expect '}' after block.", "")

    def test_trailing(self):
        self.error("1 1", "Expected end of expression", "1.0")

    def test_trailing_after_parens(self):
        self.error("(72 +)", "Expect expression.", None)

    def test_synchronize(self):
        self.error("var x = + + ; print 1;", "Expect expression.", "print 1.0;")
        self.error("var x = + + + print 1;", "Expect expression.", "print 1.0;")
