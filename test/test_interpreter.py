import io
import unittest
from time import time

from app.expression import Binary, Literal, Logical, Unary
from app.interpreter import Interpreter, RefEqualityDict, stringify, truthy
from app.resolver import static_analysis
from app.runtime import LoxRuntimeError
from app.scanner import Token
from app.scanner import TokenType as TT
from test.runner import parse, parse_expr, reraise


class TestInterpreter(unittest.TestCase):
    def validate(self, source, expected):
        expr = parse_expr(source)
        s = stringify(Interpreter(reraise).evaluate(expr))
        self.assertEqual(s, expected)

    def interpret(self, interpreter: Interpreter, source: str):
        stmt = parse(source)
        static_analysis(interpreter, stmt, reraise)
        interpreter.interpret(stmt)

    def validate_single_error_expr(self, source: str):
        """If expr has runtime error, one error nicely reported"""
        runtime_err = []
        self.interpret(Interpreter(runtime_err.append), source)
        self.assertEqual(len(runtime_err), 1)

    def validate_print(self, source, *out):
        lines = self.run_stmt(source)
        self.assertSequenceEqual(lines, out)

    def run_stmt(self, source):
        buf = io.StringIO()
        self.interpret(Interpreter(reraise, buf), source)
        return buf.getvalue().splitlines()

    def runtime_error(self, source, *out):
        buf = io.StringIO()

        def err(e: LoxRuntimeError):
            buf.write(e.message + "\n")

        self.interpret(Interpreter(err, buf), source)

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
        self.validate("-0.1", "-0.1")
        self.validate("-0", "-0")
        self.validate("--0", "0")

        self.validate_single_error_expr("-nil")

        self.validate("!true", "false")
        self.validate("!(!true)", "true")

        self.validate("!nil", "true")
        self.validate("!0", "false")
        self.validate('!""', "false")
        self.validate('!"A"', "false")

    def test_equality(self):
        self.validate("1 == 1", "true")
        self.validate("1 != 1", "false")
        self.validate("0 == nil", "false")
        self.validate("0 != 1 == true", "true")

        self.validate("true == 1", "false")
        self.validate("true != 1", "true")
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
        self.validate_print("print clock;", "<native fn>")

        (s,) = self.run_stmt("print clock();")
        self.assertAlmostEqual(float(s), time(), places=0)  # within one sec

    def test_logical(self):
        self.validate_print("print 1   and 2;", "2")
        self.validate_print("print nil and 2;", "nil")
        self.validate_print("print 1    or 2;", "1")
        self.validate_print("print nil  or 2;", "2")

        self.validate_print("print 0 or 2;", "0")  # 0 is truthy, so returned by or
        self.validate_print("print 3 and 0;", "0")

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
        self.validate_print("var x = 1; { var x = 2; print x; }", "2")

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

        # Don't test `return 1;` because it's a compile error

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

    def test_resolved_global(self):
        self.validate_print("var a = 23; var a = a; print a;", "23")

    def test_resolved_func_var(self):
        self.validate_print(
            """
var variable = "global";
{
  fun f() { print variable; }
  f();
  var variable = "local";
  f();
}""",
            "global",
            "global",
        )

        self.validate_print(
            """
fun global() { print "global"; }
{
  fun f() { global();}
  f();
  fun global() { print "local"; }
  f();
}""",
            "global",
            "global",
        )

    def test_resolved_closure_assign(self):
        self.validate_print(
            """
var count = 0;
{
  fun makeCounter() {
    fun counter() {
      // should always be global
      count = count + 1;
      print count;
    }
    return counter;
  }

  var counter1 = makeCounter();
  counter1(); // Should print 1
  counter1(); // Should print 2

  // This variable declaration shouldn't affect our counter.
  var count = 10;

  counter1(); // Should print 3
  counter1(); // Should print 4

  print count; // Should print 10
}
""",
            "1",
            "2",
            "3",
            "4",
            "10",
        )

    def test_resolved_var(self):
        self.runtime_error(
            "var x = x;", "Undefined variable 'x'."
        )  # In global scope, accessing global is a runtime error
        #  Not testing `{var x = x;}` because that is resolver error

    def test_mutate_param(self):
        self.validate_print(
            """
var A = 1;
{
    fun F(A) {
        print A;
        A=2;
        print A;
    }
    F(3);
    print A;
}
""",
            "3",
            "2",
            "1",
        )

    def test_reassign_func(self):
        self.validate_print(
            """
fun F() {
    print 1;
    F = 3;
    return 2;
}
print F;
print F();
print F;
""",
            "<fn F>",
            "1",
            "2",
            "3",
        )

    def test_class_print(self):
        self.validate_print("class A{} print A; print A();", "A", "A instance")

    def test_class_fields(self):
        self.validate_print("class A{} var a = A(); a.x = 1; print a.x;", "1")
        self.validate_print("class A{} var a = A(); a.x = nil; print a.x;", "nil")
        self.validate_print("class A{} var a = A(); print a.x = 1;", "1")
        self.runtime_error("class A{} var a = A(); a.y;", "Undefined property 'y'.")
        self.runtime_error("class A{} A.x;", "Only instances have properties.")
        self.runtime_error("class A{} A.x = 1;", "Only instances have fields.")

    def test_set_order(self):
        prelude = """
class A {}
fun F() { print 1; return A();}
fun G() { print 2; }
"""
        self.validate_print(prelude + "F().a = G();", "1", "2")
        self.runtime_error(prelude + "G().g = F();", "2", "Only instances have fields.")

    def test_methods(self):
        self.validate_print("class A{ hi() {print 1;} } A().hi();", "1")
        self.validate_print("class A{ hi() {} } print A().hi;", "<fn hi>")
        self.validate_print("class A{ hi() {print 1;} } var h = A().hi; h();", "1")
        self.validate_print("class A{ hi() {} } var a = A(); a.hi = 3; print a.hi;", "3")
        self.validate_print("fun F() {print 1;} class A{} var a = A(); a.hi = F; a.hi();", "1")
        self.validate_print("class A{ hi(x) {print x;} } A().hi(1);", "1")

    def test_this(self):
        self.validate_print("class C { f() { return this; } } print C().f();", "C instance")

    def test_this_detached(self):
        self.validate_print(
            """
class C { f() { return this.x; } }
var c = C();
var f = c.f;
c.x = 4;
print f();

var c2 = C();
c2.f = f;
print c2.f();
""",
            "4",
            "4",
        )

    def test_init(self):
        self.validate_print("class A{ init() { print 1 ;} } A();", "1")
        self.validate_print("class A{ init() { this.x = 1;} } print A().x;", "1")

        self.runtime_error("class A{} A(1);", "Expected 0 arguments but got 1.")
        self.runtime_error("class A{ init(x) { } } A();", "Expected 1 arguments but got 0.")

    def test_init_returns(self):
        self.validate_print("class A{ init() {} } print A().init();", "A instance")
        self.validate_print("class A{ init() {return;} } print A().init();", "A instance")


class TestTruthy(unittest.TestCase):
    def test_truthy(self):
        self.assertFalse(truthy(None))
        self.assertFalse(truthy(False))

        self.assertTrue(truthy(object()))
        self.assertTrue(truthy("non-empty"))
        self.assertTrue(truthy(1))
        self.assertTrue(truthy(0.1))
        self.assertTrue(truthy(""))
        self.assertTrue(truthy(0))


class TestRefEqualityDict(unittest.TestCase):
    def test_ref_equality_dict(self):
        d = RefEqualityDict()
        a, b = object(), object()

        d[a] = 1
        d[b] = 2
        self.assertEqual(d[a], 1)
        self.assertIn(a, d)

        del d[a]
        self.assertNotIn(a, d)
        self.assertIn(b, d)

        self.assertEqual(len(d), 1)
