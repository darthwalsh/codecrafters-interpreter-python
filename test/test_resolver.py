import io
import unittest

from app.interpreter import Interpreter
from app.resolver import Resolver
from test.runner import parse, reraise


class TestResolver(unittest.TestCase):
    def error(self, source, *out):
        errs = []
        buf = io.StringIO()

        stmt = parse(source)
        interpreter = Interpreter(reraise, buf)
        Resolver(interpreter, on_error=errs.append).resolve(stmt)

        self.assertSequenceEqual(buf.getvalue(), "")  # Shouldn't have side effects
        self.assertSequenceEqual([str(e) for e in errs], out)

    def test_resolved_var(self):
        self.error(
            "{var x = x;}",
            "Can't read local variable in its own initializer.",
        )

    def test_redeclared(self):
        self.error("{var x = 1; var x = 2;}", "Already a variable with this name in this scope.")
