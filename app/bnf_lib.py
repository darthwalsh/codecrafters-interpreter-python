import math
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

M_VAR_MAX = 6


def solo(items, default=None):
    if len(items) == 1:
        return next(iter(items))
    return default or items


# TODO trim this functionality by running `coverage run -m unittest test.test_bnf_lib.TestBnf.test_load ; coverage xml` and find unused features.
# MAYBE try to get original production.bnf to work, with special i.e. <any char except "\"">
class Bnf:
    """Automatic parse rule based on bnf rule text

    Spec 4.1. Production Syntax
    Represents different entries using python expressions:
      - Atomic terms:
      "abc"                Text string is str "abc" (no backslash escaping)
      'c'                  Text character is str "c" (no backslash escaping)
      x30                  Escaped character is str "0"
      [xA0-xD7FF]          Character range is exclusive range(0xA0, 0xD800)
      term                 Production is tuple ("rule", "term")
      - Special productions also produce regex (different DOTALL)
      <any char except "\"">
      "a" "b"              Concatenation is tuple ("concat", "a", "b")
      "a" | "b"            Alternation is frozenset({"a", "b"})
      "a"?                 Option is tuple ("repeat", 0, 1, "a")
      "a"*                 Repeat is tuple ("repeat", 0, inf, "a")
      "a"+                 Repeat is tuple ("repeat", 1, inf, "a")
      "a"{4}               Repeat is tuple ("repeat", 4, 4, "a")
      dig - "0" - "1"      Difference is tuple ("diff", ("rule", "dig"), "0", "1")

      # EOF                End of whole text stream is ("$",)
      # UPPERCASE rule names just takes substring, and skips over whitespace and //comment rule
    """

    def __init__(self, text: str):
        # '# Comments' shouldn't have semantics
        self.text = re.sub(r"# .*", "", text).strip()

        # TODO some comments have semantics!
        # Not in spec...
        self.text = re.sub(r"/\*.*?\*/", "", self.text, flags=re.DOTALL)
        self.i = 0
        self.expr = self.parse()
        if self.i < len(self.text):
            raise ValueError("remaining", self.text[self.i : self.i + 10], "got", self.expr)

    def parse(self):
        return self.parseOr()

    def parseOr(self):
        items = set()
        while True:
            items.add(self.parseConcat())
            if not self.try_take(r"\|"):
                return solo(frozenset(items))

    def parseConcat(self):
        items = []
        while True:
            item = self.parseDiff()
            if item:
                items.append(item)
            else:
                return solo(items, ("concat", *items))

    def parseDiff(self):
        subtrahend = self.parseRepeat()
        minuends = []
        while self.try_take("-"):
            minuends.append(self.parseRepeat())
        if minuends:
            return ("diff", subtrahend, *minuends)
        return subtrahend

    def parseRepeat(self):
        e = self.parseSingle()
        if c := self.try_take("[+?*{]"):
            lo, hi = 0, math.inf
            if c == "+":
                lo = 1
            elif c == "?":
                hi = 1
            elif c == "{":
                lo = hi = int(self.take(r"\d+"))
                self.take("}")
            return ("repeat", lo, hi, e)
        return e

    # Rule names can contain '+' so if followed by a letter it's part of the name not a regex repeat.
    ident_reg = r"^((?:[\w-]|\+\w)+)(\([\w(),<≤/\+-]+\))?"

    def parseSingle(self):
        if self.try_take('"'):
            return self.parseString()
        if self.try_take("'"):
            c = self.take()  # \ isn't used as an escape
            self.take("'")
            return c
        elif self.try_take("x"):
            return chr(int(self.take(r"[0-9A-F]{1,6}"), 16))
        elif self.try_take(r"\[x"):
            begin = int(self.take(r"[0-9A-F]{1,6}"), 16)
            self.take("-x")
            end = int(self.take(r"[0-9A-F]{1,6}"), 16) + 1
            self.take(r"\]")
            return range(begin, end)
        elif name := self.try_take(Bnf.ident_reg):
            match = re.match(Bnf.ident_reg, name)
            name, args = match.groups()
            if args:
                raise NotImplementedError("TODO Lox Grammar doesn't need args")
            if "(" in name:
                raise ValueError(name)

            args = args.strip("()").split(",") if args else ()
            return "rule", name, *args
        elif self.try_take(r"\[ look"):
            return self.parseLookaround()
        elif self.try_take(r'<any char except "\\"">'):
            return ("diff", range(0, 0x10FFFF), '"')
        elif self.try_take(r"\("):
            parens = self.parse()
            self.take(r"\)")
            return parens
        else:
            return None

    def parseLookaround(self):
        if self.try_take("ahead"):
            pos = bool(self.try_take("="))
            if not pos:
                self.take("≠")
            e = self.parseSingle()
            self.take("]")
            return ("?=" if pos else "?!", e)

        self.take("behind =")
        e = self.parseSingle()
        self.take("]")
        return ("?<=", e)

    def parseString(self):
        cs = []
        while not self.try_take('"'):
            cs.append(self.take())
        return "".join(cs)

    def try_take(self, pattern=".") -> str:
        m = re.match(pattern, self.text[self.i :])
        if not m:
            return None
        s = m.group()
        self.i += len(s)
        self.try_take(r"\s+")
        return s

    def take(self, pattern="."):
        s = self.try_take(pattern)
        if not s:
            raise ValueError("expected", pattern, "at", self.text[self.i : self.i + 10])
        return s


def split_defs(bnf_text):
    lines = bnf_text.split("\n")
    def_lines = [i for i, line in enumerate(lines) if "→" in line] + [len(lines)]

    for b, e in zip(def_lines, def_lines[1:]):
        def_str = "\n".join(lines[b:e]).strip()
        name, text = (s.strip() for s in def_str.split("→"))
        yield name, text


@dataclass(frozen=True)
class ParseResult:
    rule: str
    start: int
    end: int
    expr: object

    def __str__(self):
        if self.rule.isupper():
            if isinstance(self.expr, str):
                return self.expr
            raise ValueError(self.expr)

        if isinstance(self.expr, tuple):
            expr = ', '.join(map(str, self.expr))
        else:
            expr = str(self.expr)
        return f"{self.rule}({expr})"
    
    def __repr__(self):
        return str(self)


def untuple(o: object):
    if isinstance(o, tuple):
        result = []
        for t in o:
            t = untuple(t)
            if t != ():
                result.append(t)
        if len(result) == 1:
            return result[0]
        return tuple(result)
    return o


class Lib:
    def __init__(self):
        self.bnf = {}
        self.load_defs()

    def load_defs(self):
        productions_path = (Path(__file__).parent / "productions.bnf").resolve()
        with open(productions_path, encoding="utf-8") as f:
            productions = f.read()

        for name, text in split_defs(productions):
            try:
                rule = Bnf(text.strip(";"))
            except Exception as e:
                raise type(e)(f"{name}: {e!s}").with_traceback(sys.exc_info()[2])
            self.bnf.setdefault(name, []).append(rule.expr)
        self.bnf["EOF"] = [("$",)]

    def parse(self, text: str, expr):
        self.text = text

        results = set()
        for result, lastI in self.resolve(0, expr, skip_ws=True):
            if self.ignore_whitespace(lastI) == len(text):
                results.add(result)

        if not results:
            raise ValueError("no results")
        return solo(results)

    def ignore_whitespace(self, i: int) -> int:
        if i + 1 < len(self.text) and self.text[i : i + 2] == "//":
            try:
                return self.ignore_whitespace(1 + self.text.index("\n", i))
            except ValueError:
                return len(self.text)
        if i < len(self.text) and self.text[i].isspace():
            return self.ignore_whitespace(i + 1)
        return i

    def resolve(self, i: int, expr, skip_ws) -> Iterator[tuple[object, int]]:  # TODO Iterator[ParseResult]? Or should it be less lazy and return list[ParseResult]?
        if skip_ws:
            i = self.ignore_whitespace(i)
        match expr:
            case str(s):
                if i < len(self.text) and self.text[i:i+len(s)] == s:
                    yield s, i + len(s)
            case range():
                if i < len(self.text) and ord(self.text[i]) in expr:
                    yield self.text[i], i + 1
            case set() | frozenset():
                for e in expr:
                    yield from self.resolve(i, e, skip_ws)
            case ("concat",):
                yield (), i
            case ("concat", e, *exprs):
                for vv, ii in self.resolve(i, e, skip_ws):
                    for vvv, iii in self.resolve(ii, ("concat", *exprs), skip_ws):
                        yield (vv,) + vvv, iii
            case ("repeat", lo, hi, e):
                if not lo:
                    yield (), i
                if hi:
                    dec = ("repeat", max(lo - 1, 0), hi - 1, e)
                    for vv, ii in self.resolve(i, e, skip_ws):
                        for vvv, iii in self.resolve(ii, dec, skip_ws):
                            yield (vv,) + vvv, iii
            case ("rule", name):
                for expr in self.bnf[name]:
                    literal_text = name.isupper()
                    for e, ii in self.resolve(i, expr, skip_ws=not literal_text):
                        e = untuple(e)
                        if literal_text:
                            yield ParseResult(name, i, ii, self.text[i : ii]), ii
                        elif isinstance(e, ParseResult):
                            yield e, ii
                        else:
                            yield ParseResult(name, i, ii, e), ii
            case ("diff", e, *subtrahends):
                for s in subtrahends:
                    for o in self.resolve(i, s, skip_ws):
                        return
                if not any(
                    any(self.resolve(i, s, skip_ws)) for s in subtrahends
                ): # TODO this duplicates above??
                    yield from self.resolve(i, e, skip_ws)
            case ("$",):
                if i == len(self.text):
                    yield "", i
            case _:
                raise ValueError("unknown type:", expr)
