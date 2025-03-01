import math
import unittest

from app.bnf_lib import Bnf, Lib, ParseResult, untuple

unittest.util._MAX_LENGTH = 2000  # type: ignore


class TestBnf(unittest.TestCase):
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
        g = Bnf("nb-json")
        self.assertEqual(g.expr, ("rule", "nb-json"))

    def test_lookarounds(self):
        g = Bnf("[ lookahead ≠ ns-char ]")
        self.assertEqual(g.expr, ("?!", ("rule", "ns-char")))

        g = Bnf("[ lookbehind = ns-char ]")
        self.assertEqual(g.expr, ("?<=", ("rule", "ns-char")))

    def test_special(self):
        g = Bnf('<any char except "\\"">')
        self.assertEqual(g.expr, ("diff", range(0, 0x10FFFF), '"'))

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
        self.assertEqual(len(Lib().bnf), 32)


library = Lib()


class TestLib(unittest.TestCase):
    def test_single_char(self):
        self.assertEqual(library.parse("c", "c"), "c")

    def test_str(self):
        self.assertEqual(library.parse("az", ("concat", "a", "z")), tuple("az"))

    def test_concat(self):
        self.assertEqual(library.parse("a3z", ("concat", "a", range(0x30, 0x3A), "z")), tuple("a3z"))

    def test_empty(self):
        self.assertEqual(library.parse("", ("concat",)), ())

    def test_range(self):
        self.assertEqual(library.parse("2", range(0x30, 0x3A)), "2")

    def test_or(self):
        self.assertEqual(library.parse("0", {"0", "9"}), "0")

    def test_or_repeat(self):
        self.assertEqual(library.parse("0", {"0", "0"}), "0")

    def test_star(self):
        self.assertEqual(library.parse("a", ("repeat", 0, math.inf, "a")), ("a",))

    def test_plus(self):
        self.assertEqual(library.parse("a", ("repeat", 1, math.inf, "a")), ("a",))

    def test_plus_not_match(self):
        self.assertEqual(library.parse("b", {"b", ("repeat", 1, math.inf, "a")}), "b")

    def test_times(self):
        self.assertEqual(library.parse("aaa", ("repeat", 3, 3, "a")), tuple("aaa"))

    def test_rules(self):
        self.assertEqual(library.parse("x2A", ("rule", "IDENTIFIER")), ParseResult("IDENTIFIER", 0, 3, "x2A"))

    def test_white_space(self):
        self.assertEqual(library.parse(" c", "c"), "c")
        self.assertEqual(library.parse("c ", "c"), "c")
        self.assertEqual(library.parse("c c", ("concat", "c", "c")), tuple("cc"))

        self.assertEqual(library.parse('"AB"', ("rule", "STRING")), ParseResult("STRING", 0, 4, '"AB"'))
        self.assertEqual(library.parse('" B"', ("rule", "STRING")), ParseResult("STRING", 0, 4, '" B"'))
        self.assertEqual(library.parse('"A "', ("rule", "STRING")), ParseResult("STRING", 0, 4, '"A "'))

        self.assertEqual(library.parse("c//COM", "c"), "c")
        self.assertEqual(library.parse("c //COM\nc", ("concat", "c", "c")), tuple("cc"))

    def test_end(self):
        self.assertEqual(
            library.parse("a", ("concat", "a", ("rule", "EOF"))),
            ("a", ParseResult(rule="EOF", start=1, end=1, expr="")),
        )

        with self.assertRaises(ValueError) as e_info:
            library.parse("a", ("rule", "EOF"))
        self.assertIn("no results", str(e_info.exception))
        with self.assertRaises(ValueError) as e_info:
            library.parse("a", ("concat", ("rule", "EOF"), "a"))
        self.assertIn("no results", str(e_info.exception))

    def test_diff(self):
        diff = ("diff", range(0x20, 0x7F), "0", range(0x35, 0x3A))

        self.assertEqual(library.parse("1", diff), "1")

        with self.assertRaises(ValueError) as e_info:
            library.parse("0", diff)
        self.assertIn("no results", str(e_info.exception))

        with self.assertRaises(ValueError) as e_info:
            library.parse("5", diff)
        self.assertIn("no results", str(e_info.exception))

    def test_tree_repeat(self):
        self.assertEqual(
            split_parse_result(library.parse("ABCD", ("repeat", 4, 4, ("rule", "ALPHA")))),
            (("ALPHA", "A"), ("ALPHA", "B"), ("ALPHA", "C"), ("ALPHA", "D")),
        )

    def test_tree_rule(self):
        self.assertEqual(
            split_parse_result(library.parse("1+2", ("rule", "term"))),
            ("term", (("NUMBER", "1"), ("+", ("NUMBER", "2")))),
        )
        self.assertEqual(
            split_parse_result(library.parse("1+2*3", ("rule", "term"))),
            (
                "term",
                (("NUMBER", "1"), ("+", ("factor", (("NUMBER", "2"), ("*", ("NUMBER", "3")))))),
            ),
        )


def split_parse_result(pr: ParseResult | object):
    if isinstance(pr, tuple):
        return tuple(split_parse_result(p) for p in pr)
    if isinstance(pr, ParseResult):
        return pr.rule, split_parse_result(pr.expr)
    return pr


class TestUntuple(unittest.TestCase):
    def test_untuple(self):
        a, b, c = "abc"
        self.assertEqual(untuple(a), a)
        self.assertEqual(untuple((a,)), a)
        self.assertEqual(untuple(()), ())
        self.assertEqual(untuple(((),)), ())

        self.assertEqual(untuple((a, b, ())), (a, b))
        self.assertEqual(untuple((a, ())), a)

        self.assertEqual(untuple(((a, b, ()), c)), ((a, b), c))


if __name__ == "__main__":
    unittest.main()
