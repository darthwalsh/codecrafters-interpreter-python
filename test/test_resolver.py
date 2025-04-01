import io
import unittest

from app.interpreter import Interpreter
from app.resolver import static_analysis
from app.scanner import Token
from app.scanner import TokenType as TT
from test.runner import parse_stmt, reraise


class TestResolver(unittest.TestCase):
    def error(self, source, *out):
        errs = []
        buf = io.StringIO()

        def callback(token: Token, message: str):
            lexeme = f"'{token.lexeme}'" if token.type != TT.EOF else "end"
            errs.append(f"Error at {lexeme}: {message}")

        static_analysis(Interpreter(reraise, buf), parse_stmt(source), callback)

        self.assertSequenceEqual(buf.getvalue(), "")  # Shouldn't have side effects
        self.assertSequenceEqual([str(e) for e in errs], out)

    def no_error(self, source):
        self.error(source)

    def test_resolved_var(self):
        self.error(
            "var x = 1; {var x = x;}", "Error at 'x': Can't read local variable in its own initializer."
        )
        self.error("{var x = x;}", "Error at 'x': Can't read local variable in its own initializer.")

    def test_redeclared(self):
        xx = "Error at 'x': Already a variable with this name in this scope."

        self.no_error("var x = 1; {var x = 2;}")
        self.error("{var x = 1; var x = 2;}", xx)
        self.no_error("{var x = 1; {var x = 2;} }")
        self.error("{var x = 1; fun x(){}}", xx)
        self.error("{var x = 1; class x{}}", xx)

        self.no_error("{ var x = 1; fun f(x) {x;} }")
        self.error("fun f(x) {var x = 1;}", xx)
        self.no_error("fun x() {var x = 1;}")
        self.no_error("fun x() {fun x() {} }")

    def test_func_params(self):
        self.no_error("{ var x = 1; fun f(x) { } }")
        self.error("fun f(ab, ab) { }", "Error at 'ab': Already a variable with this name in this scope.")

    def test_return(self):
        self.error("return 1;", "Error at 'return': Can't return from top-level code.")
        self.error("return;", "Error at 'return': Can't return from top-level code.")

        self.error("while (1) { return 1; }", "Error at 'return': Can't return from top-level code.")

        self.no_error("fun f() { return 1; }")
        self.no_error("fun f() { { return 1; } }")
