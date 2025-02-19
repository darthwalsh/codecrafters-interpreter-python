import unittest

from app.scanner import Scanner
from test.runner import reraise


class TestRunner(unittest.TestCase):
    def test_reraise(self):
        nie = NotImplementedError()
        with self.assertRaises(AssertionError) as e:
            reraise(nie)
        self.assertEqual(e.exception.__cause__, nie)

        with self.assertRaises(AssertionError) as e:
            Scanner("$", reraise).scan_tokens()
        self.assertEqual(e.exception.args[2], "Unexpected character: $")
