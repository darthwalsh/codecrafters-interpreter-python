import io
import unittest

from app.interpreter import Interpreter
from app.resolver import static_analysis
from test.runner import parse_stmt, reraise


class TestResolver(unittest.TestCase):
    def error(self, source, *out):
        errs = []
        buf = io.StringIO()

        static_analysis(Interpreter(reraise, buf), parse_stmt(source), on_error=errs.append)

        self.assertSequenceEqual(buf.getvalue(), "")  # Shouldn't have side effects
        self.assertSequenceEqual([str(e) for e in errs], out)

    def no_error(self, source):
        self.error(source)

    def test_resolved_var(self):
        self.error("var x = 1; {var x = x;}", "Can't read local variable in its own initializer.")
        self.error("{var x = x;}", "Can't read local variable in its own initializer.")

    def test_redeclared(self):
        self.no_error("var x = 1; {var x = 2;}")
        self.error("{var x = 1; var x = 2;}", "Already a variable with this name in this scope.")
        self.no_error("{var x = 1; {var x = 2;} }")

    def test_return(self):
        self.error("return 1;", "Can't return from top-level code.")
        self.error("return;", "Can't return from top-level code.")

        self.error("while (1) { return 1; }", "Can't return from top-level code.")

        self.no_error("fun f() { return 1; }")
        self.no_error("fun f() { { return 1; } }")
