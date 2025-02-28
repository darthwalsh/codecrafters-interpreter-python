import math
import unittest

from app.bnf_lib import Bnf, Lib


class TestBnfLib(unittest.TestCase):
    def test_char(self):
        g = Bnf('"c"')
        self.assertEqual(g.expr, "c")

    def test_string(self):
        g = Bnf('"abc"')
        self.assertEqual(g.expr, "abc")

    def test_singlequote(self):
        g = Bnf("'$'")
        self.assertEqual(g.expr, "$")

    def test_singlequote_backslash(self):
        g = Bnf("'\\'")
        self.assertEqual(g.expr, "\\")

    def test_str(self):
        g = Bnf('"y" "a" "m" "l"')
        self.assertEqual(g.expr, ("concat", "y", "a", "m", "l"))

    def test_unicode(self):
        g = Bnf("x9")
        self.assertEqual(g.expr, "\x09")
        g = Bnf("x10FFFF")
        self.assertEqual(g.expr, "\U0010ffff")

    def test_range(self):
        g = Bnf("[x30-x39]")
        self.assertEqual(g.expr, range(0x30, 0x3A))
        g = Bnf("[xA0-xD7FF]")
        self.assertEqual(g.expr, range(0xA0, 0xD800))

    def test_rules(self):
        g = Bnf("s-indent(<n)")
        self.assertEqual(g.expr, ("rule", "s-indent", "<n"))

        g = Bnf("nb-json")
        self.assertEqual(g.expr, ("rule", "nb-json"))

        g = Bnf("s-separate(n,c)")
        self.assertEqual(g.expr, ("rule", "s-separate", "n", "c"))

    def test_lookarounds(self):
        g = Bnf("[ lookahead = ns-plain-safe(c) ]")
        self.assertEqual(g.expr, ("?=", ("rule", "ns-plain-safe", "c")))

        g = Bnf("[ lookahead ≠ ns-char ]")
        self.assertEqual(g.expr, ("?!", ("rule", "ns-char")))

        g = Bnf("[ lookbehind = ns-char ]")
        self.assertEqual(g.expr, ("?<=", ("rule", "ns-char")))

    def test_special(self):
        g = Bnf("<start-of-line>")
        self.assertEqual(g.expr, ("^",))

        g = Bnf("<end-of-input>")
        self.assertEqual(g.expr, ("$",))

        g = Bnf("<empty>")
        self.assertEqual(g.expr, ("concat",))

    def test_or(self):
        g = Bnf('"0" | "9"')
        self.assertEqual(g.expr, {"0", "9"})

    def test_opt(self):
        g = Bnf('"a"?')
        self.assertEqual(g.expr, ("repeat", 0, 1, "a"))

    def test_star(self):
        g = Bnf('"a"*')
        self.assertEqual(g.expr, ("repeat", 0, math.inf, "a"))

    def test_plus(self):
        g = Bnf('"a"+')
        self.assertEqual(g.expr, ("repeat", 1, math.inf, "a"))

    def test_curlyrepeat(self):
        g = Bnf('"a"{4}')
        self.assertEqual(g.expr, ("repeat", 4, 4, "a"))

    def test_diff(self):
        g = Bnf("dig - x30")
        self.assertEqual(g.expr, ("diff", ("rule", "dig"), "0"))

    def test_2diff(self):
        g = Bnf("dig - x30 - x31")
        self.assertEqual(g.expr, ("diff", ("rule", "dig"), "0", "1"))

    def test_parens(self):
        g = Bnf('"x" (hex{2} ) "-"')
        self.assertEqual(g.expr, ("concat", "x", ("repeat", 2, 2, ("rule", "hex")), "-"))

    def test_empty(self):
        g = Bnf(" ")
        self.assertEqual(g.expr, ("concat",))

    def test_comment(self):
        g = Bnf(" dig /* Empty */ ")
        self.assertEqual(g.expr, ("rule", "dig"))

    def test_commenthash(self):
        g = Bnf(" # Empty ")
        self.assertEqual(g.expr, ("concat",))

    def test_comments(self):
        g = Bnf("[x41-x46] # A-F \n| [x61-x66] # a-f ")
        self.assertEqual(g.expr, {range(0x41, 0x47), range(0x61, 0x67)})

    def test_remaining(self):
        with self.assertRaises(ValueError) as e_info:
            Bnf('"1" ^^garbage')
        self.assertIn("garbage", str(e_info.exception))
        self.assertIn("remaining", str(e_info.exception))

    def test_bad_string(self):
        with self.assertRaises(ValueError) as e_info:
            Bnf("'1\\'")
        self.assertIn("'", str(e_info.exception))
        self.assertIn("expected", str(e_info.exception))

    def test_load(self):
        self.assertEqual(len(Lib().bnf), 31)


if __name__ == "__main__":
    unittest.main()
