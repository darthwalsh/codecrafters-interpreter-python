import io
import unittest
from time import time

from app.expression import Binary, Literal, Logical, Unary
from app.interpreter import Interpreter, stringify
from app.runtime import LoxRuntimeError
from app.scanner import Token
from app.scanner import TokenType as TT
from test.runner import parse, reraise


class TestInterpreter(unittest.TestCase):
    def validate(self, source, expected):
        interpreter = Interpreter(reraise)
        expr = parse(source)
        if isinstance(expr, list):
            raise AssertionError("Expected expression, got statements")
        s = stringify(interpreter.evaluate(expr))
        self.assertEqual(s, expected)

    def validate_single_error_expr(self, source):
        """If expr has runtime error, one error nicely reported"""
        runtime_err = []
        interpreter = Interpreter(runtime_err.append)
        interpreter.interpret(parse(source))
        self.assertEqual(len(runtime_err), 1)

    def validate_print(self, source, *out):
        lines = self.run_stmt(source)
        self.assertSequenceEqual(lines, out)

    def run_stmt(self, source):
        buf = io.StringIO()
        interpreter = Interpreter(reraise, buf)
        interpreter.interpret(parse(source))

        return buf.getvalue().splitlines()

    def runtime_error(self, source, *out):
        buf = io.StringIO()

        def err(e: LoxRuntimeError):
            buf.write(e.message)

        interpreter = Interpreter(err, buf)
        interpreter.interpret(parse(source))

        self.assertSequenceEqual(buf.getvalue().splitlines(), out)

    def test_literal(self):
        self.validate("1", "1")
        self.validate("0.234", "0.234")
        self.validate('"ab"', "ab")
        self.validate("true", "true")
        self.validate("nil", "nil")

    def test_call(self):
        self.validate_single_error_expr("1()")
        self.validate_single_error_expr("clock(1)")

    def test_grouping(self):
        self.validate("(1)", "1")
        self.validate("((1))", "1")

    def test_unary(self):
        self.validate("-73", "-73")
        self.validate("--12", "12")

        self.validate_single_error_expr("-nil")

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
        self.validate("1 > 1", "false")
        self.validate("4 >= 5", "false")
        self.validate("4 <= 5", "true")

        self.validate_single_error_expr('"A" < "B"')

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

        self.validate_single_error_expr('"A" * 3')

    def test_concat(self):
        self.validate('"A" + "B"', "AB")

        self.validate_single_error_expr('"A" + 3')
        self.validate_single_error_expr('3 + "A"')

    def test_clock(self):
        self.validate_print("print clock;", "<fn clock>")

        (s,) = self.run_stmt("print clock();")
        self.assertAlmostEqual(float(s), time(), places=0)  # within one sec

    def test_logical(self):
        self.validate_print("print 1   and 2;", "2")
        self.validate_print("print nil and 2;", "nil")
        self.validate_print("print 1    or 2;", "1")
        self.validate_print("print nil  or 2;", "2")

        self.validate_print("var x = 1; true  and (x=2); print x;", "2")
        self.validate_print("var x = 1; false and (x=2); print x;", "1")
        self.validate_print("var x = 1; true   or (x=2); print x;", "1")
        self.validate_print("var x = 1; false  or (x=2); print x;", "2")

    def test_assign(self):
        self.validate_print("var x; print x = 3; print x;", "3", "3")

        self.runtime_error("y = 2;", "Undefined variable 'y'.")

    def test_function(self):
        self.validate_print("fun a() { print 1.0; } a(); ", "1")
        self.validate_print("fun a(x) { print x; } a(1); a(2); ", "1", "2")

        self.validate_print("fun a(x) {} print a; ", "<fn a>")

    def test_closure(self):
        self.validate_print(
            """
fun makeCounter() { 
    var i = 0;
    fun count() {
        i = i + 1;
        print i;
    } 
    return count;
}

var counter = makeCounter();
counter();
counter();
""",
            "1",
            "2",
        )

    def test_var(self):
        self.validate_print("var x = 1 + 2; print x;", "3")
        self.validate_print("var x; print x;", "nil")
        self.validate_print("var x = 1; var x = 2; print x;", "2")

        self.runtime_error("print x; print 1;", "Undefined variable 'x'.")

    def test_block(self):
        self.validate_print("var x = 1; {x = 2; print x; } print x; ", "2", "2")
        self.validate_print("var x = 1; {var x = 2; print x; } print x; ", "2", "1")

    def test_if(self):
        self.validate_print("if (true)  print 1;", "1")
        self.validate_print("if (false) print 1;")
        self.validate_print("if (true)  print 1; else print 2;", "1")
        self.validate_print("if (false) print 1; else print 2;", "2")

    def test_return(self):
        self.validate_print("fun b(a) { return a; } print b(1);", "1")
        self.validate_print("fun b() { return; } print b();", "nil")
        self.validate_print("fun b() { } print b();", "nil")

        self.validate_print("fun a() {} fun b() { return a; } print b();", "<fn a>")
        self.validate_print("fun a() { return a; } fun b() { return a; } print b()();", "<fn a>")
        self.validate_print("fun a() { return a; } fun b() { return a; } print b()()();", "<fn a>")

        self.validate_print("fun b() {{{ return 1; }}} print b();", "1")

        self.runtime_error("return 1;", "Tried to return '1' outside function.")

    @unittest.skip("For loop not implemented")  # TODO For loop not implemented"
    def test_while(self):
        self.validate_print("var x = 0; while (x < 3) { x = x + 1; print x; }", "1", "2", "3")
        self.validate_print("var x = 0; while (x < 3) { print x = x + 1; }", "1", "2", "3")
        self.validate_print("while (false) { print 2; }")

        self.validate_print("for (var x = 0; x < 3;) print x = x + 1;", "1", "2", "3")

    def test_statements(self):
        self.validate_print("1;")
        self.validate_print("print 1;", "1")
        self.validate_print("print 1; print 1.2;", "1", "1.2")

    def test_impossible(self):
        with self.assertRaises(RuntimeError) as e:
            Interpreter(reraise).visit_unary(Unary(Token(TT.WHILE, "while", 1, None), Literal(1.0)))
        assert str(e.exception) == "Impossible state"

        with self.assertRaises(RuntimeError) as e:
            Interpreter(reraise).visit_binary(
                Binary(Literal(1.0), Token(TT.AND, "and", 1, None), Literal(1.0))
            )
        assert str(e.exception) == "Impossible state"

        with self.assertRaises(RuntimeError) as e:
            Interpreter(reraise).visit_logical(
                Logical(Literal(1.0), Token(TT.PLUS, "+", 1, None), Literal(1.0))
            )
        assert str(e.exception) == "Impossible state"

    def test_validate(self):
        with self.assertRaises(AssertionError) as e:
            self.validate("1;", "whatever")
        self.assertEqual(str(e.exception), "Expected expression, got statements")
