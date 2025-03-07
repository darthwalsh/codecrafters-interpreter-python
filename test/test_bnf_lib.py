import math
import unittest

from app.bnf_lib import Bnf, Lib, Parse, de_tree

unittest.util._MAX_LENGTH = 2000  # type: ignore


def bnf(text):
    return Bnf(text + ";").expr


class TestBnf(unittest.TestCase):
    def test_char(self):
        self.assertEqual(bnf('"c"'), "c")

    def test_string(self):
        self.assertEqual(bnf('"abc"'), "abc")

        self.assertEqual(bnf('"\\""'), '"')
        self.assertEqual(bnf('"a\\""'), 'a"')
        self.assertEqual(bnf('"\\"a"'), '"a')

        self.assertEqual(bnf('"y" "a" "m" "l"'), ("concat", "y", "a", "m", "l"))

        with self.assertRaises(ValueError):
            bnf('"a')
        with self.assertRaises(ValueError):
            bnf('"\\a"')

    def test_range(self):
        self.assertEqual(bnf('"0" ... "9"'), range(0x30, 0x3A))

    def test_rules(self):
        self.assertEqual(bnf("statement"), ("rule", "statement"))

    def test_special(self):
        self.assertEqual(bnf('<any char except "\\"">'), ("non_double_quote",))

    def test_or(self):
        self.assertEqual(bnf('"0" | "9"'), ["0", "9"])

    def test_opt(self):
        self.assertEqual(bnf('"a"?'), ("optional", "a"))

    def test_star(self):
        self.assertEqual(bnf('"a"*'), ("repeat", 0, math.inf, "a"))

    def test_plus(self):
        self.assertEqual(bnf('"a"+'), ("repeat", 1, math.inf, "a"))

    def test_parens(self):
        self.assertEqual(
            bnf('"x" (hex hex) "-"'), ("concat", "x", ("concat", ("rule", "hex"), ("rule", "hex")), "-")
        )

    def test_empty(self):
        self.assertEqual(bnf(" "), ("concat",))

    def test_comment(self):
        self.assertEqual(bnf(" dig /* Empty */ "), ("rule", "dig"))

    def test_comments(self):
        self.assertEqual(bnf("dig /* A-F */\n| bar /* a-f */"), [("rule", "dig"), ("rule", "bar")])

    def test_remaining(self):
        with self.assertRaises(ValueError) as e_info:
            bnf('"1"; ^^garbage')
        self.assertIn("garbage", str(e_info.exception))
        self.assertIn("remaining", str(e_info.exception))

    def test_bad_string(self):
        with self.assertRaises(ValueError) as e_info:
            bnf('"\\ "')
        self.assertIn("'", str(e_info.exception))
        self.assertIn("expected", str(e_info.exception))

    def test_compose_concat_optional(self):
        optional = bnf('"A" ("a" "b")?')
        self.assertEqual(parse("Aab", optional), ("A", ("a", "b")))
        self.assertEqual(parse("A", optional), ("A", None))

        concat = bnf('"a" "b"? "c" "d"?')
        self.assertEqual(parse("ac", concat), ("a", None, "c", None))
        self.assertEqual(parse("abc", concat), ("a", "b", "c", None))
        self.assertEqual(parse("abcd", concat), ("a", "b", "c", "d"))
        self.assertEqual(parse("acd", concat), ("a", None, "c", "d"))

    def test_load(self):
        defs = Lib().bnf
        self.assertIn("STRING", defs)

    def test_load_dupe(self):
        with self.assertRaises(ValueError) as e_info:
            Lib().load_production_rules('DIGIT          → "0" ... "9" ;\nDIGIT          → "0" ... "9" ;')
        self.assertIn("duplicate", str(e_info.exception))

    def test_load_bad(self):
        with self.assertRaises(ValueError) as e_info:
            Lib().load_production_rules("CUSTOM → abc")
        self.assertIn("CUSTOM", str(e_info.exception))


class TestDeTree(unittest.TestCase):
    def test_de_tree(self):
        s = "abc"
        p = Parse("IDENTIFIER", s)
        unary = Parse("unary", p)
        self.assertEqual(de_tree(s), s)
        self.assertEqual(de_tree((s,)), (s,))

        self.assertEqual(de_tree(unary), p)
        self.assertEqual(de_tree(Parse("unary", (p,))), p)
        self.assertEqual(de_tree(Parse("unary", ())), Parse("unary", ()))
        self.assertEqual(de_tree(Parse("unary", (p, p))), Parse("unary", (p, p)))

        call_with_list = Parse("call", ["list type doesn't unpack unary", unary])
        self.assertEqual(de_tree(call_with_list), call_with_list)


try:
    library = Lib()
except Exception as e:
    print(e)  # pragma: no cover


def parse(source, expr):
    return library.parse(source, expr)


class TestLib(unittest.TestCase):
    def test_single_char(self):
        self.assertEqual(parse("c", "c"), "c")
        self.assertEqual(parse("cd", "cd"), "cd")

    def test_str(self):
        self.assertEqual(parse("az", ("concat", "a", "z")), tuple("az"))

    def test_concat(self):
        self.assertEqual(parse("a3z", ("concat", "a", range(0x30, 0x3A), "z")), tuple("a3z"))

    def test_empty(self):
        self.assertEqual(parse("", ("concat",)), ())

    def test_range(self):
        self.assertEqual(parse("2", range(0x30, 0x3A)), "2")

    def test_or(self):
        self.assertEqual(parse("0", ["0", "9"]), "0")

    def test_or_repeat(self):
        # Removed this functionality from bnf_lib, as it wasn't needed.
        with self.assertRaises(ValueError) as e_info:
            parse("0", ["0", "0"])
        self.assertIn("ambiguous", str(e_info.exception))

    def test_star(self):
        self.assertEqual(parse("a", ("repeat", 0, math.inf, "a")), ("a",))

    def test_plus(self):
        self.assertEqual(parse("a", ("repeat", 1, math.inf, "a")), ("a",))

    def test_plus_not_match(self):
        self.assertEqual(parse("b", ["b", ("repeat", 1, math.inf, "a")]), "b")

    def test_times(self):
        self.assertEqual(parse("aaa", ("repeat", 3, 3, "a")), tuple("aaa"))

    def test_rules(self):
        self.assertEqual(parse("x2A", ("rule", "IDENTIFIER")), Parse("IDENTIFIER", "x2A"))

    def test_identifier_hack(self):
        with self.assertRaises(ValueError) as e_info:
            parse("nil", ("rule", "IDENTIFIER"))
        self.assertIn("no results", str(e_info.exception))

        self.assertEqual(parse("nil", ("rule", "primary")), Parse("primary", "nil"))

        self.assertEqual(parse("nil2", ("rule", "IDENTIFIER")), Parse("IDENTIFIER", "nil2"))

    def test_white_space(self):
        self.assertEqual(parse(" c", "c"), "c")
        self.assertEqual(parse("c ", "c"), "c")
        self.assertEqual(parse("c c", ("concat", "c", "c")), tuple("cc"))

        self.assertEqual(parse('"AB"', ("rule", "STRING")), Parse("STRING", '"AB"'))
        self.assertEqual(parse('" B"', ("rule", "STRING")), Parse("STRING", '" B"'))
        self.assertEqual(parse('"A "', ("rule", "STRING")), Parse("STRING", '"A "'))

        self.assertEqual(parse("c//COM", "c"), "c")
        self.assertEqual(parse("c //COM\nc", ("concat", "c", "c")), tuple("cc"))

    def test_end(self):
        self.assertEqual(
            parse("a", ("concat", "a", ("rule", "EOF"))),
            ("a", Parse("EOF", "")),
        )

        with self.assertRaises(ValueError) as e_info:
            parse("a", ("rule", "EOF"))
        self.assertIn("no results", str(e_info.exception))
        with self.assertRaises(ValueError) as e_info:
            parse("a", ("concat", ("rule", "EOF"), "a"))
        self.assertIn("no results", str(e_info.exception))

    def test_tree_repeat(self):
        self.assertEqual(
            parse("AB", ("repeat", 2, 2, ("rule", "IDENTIFIER"))),
            (Parse("IDENTIFIER", "A"), Parse("IDENTIFIER", "B")),
        )
        self.assertEqual(
            parse("ABCD", ("repeat", 4, 4, ("rule", "ALPHA"))),
            (Parse("ALPHA", "A"), Parse("ALPHA", "B"), Parse("ALPHA", "C"), Parse("ALPHA", "D")),
        )

    def test_tree_rule(self):
        self.assertEqual(
            de_tree(parse("1+2", ("rule", "term"))),
            Parse("term", (Parse("NUMBER", "1"), (("+", Parse("NUMBER", "2")),))),
        )
        self.assertEqual(
            de_tree(parse("1+2*3", ("rule", "term"))),
            Parse(
                "term",
                (
                    Parse("NUMBER", "1"),
                    (("+", Parse("factor", (Parse("NUMBER", "2"), (("*", Parse("NUMBER", "3")),)))),),
                ),
            ),
        )

    def test_bad_expr(self):
        with self.assertRaises(RuntimeError) as e_info:
            parse("1", ("repeat", "wrong_number_of_args"))
        self.assertIn("Impossible state:", str(e_info.exception))


class TestParse(unittest.TestCase):
    def validate_str(self, source, expected, rule="expression"):
        self.assertEqual(str(de_tree(parse(source, ("rule", rule)))), expected)

    def test_string(self):
        self.validate_str("a", "_a")
        self.validate_str("1", "d1", rule="DIGIT")
        self.validate_str("", "<eof>", rule="EOF")
        self.validate_str("1", "+1")
        self.validate_str('"ab"', '"ab"')
        self.validate_str("nil", "primary(nil)")


if __name__ == "__main__":
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()
