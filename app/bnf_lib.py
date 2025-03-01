import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

M_VAR_MAX = 6


def solo(items, default=None):
    if len(items) == 1:
        return next(iter(items))
    return default or items

class Bnf:
    """Automatic parse rule based on bnf rule text

    Spec 4.1. Production Syntax
    Represents different entries using python expressions:
      - Atomic terms:
      "abc\""              Text string is str 'abc"' (backslash can escape double quote)
      "0" ... "9"          Character range is exclusive range(0x30, 0x3A)
      term                 Production is tuple ("rule", "term")
      <any char except "\""> like it says on the tin
      "a" "b"              Concatenation is tuple ("concat", "a", "b")
      "a" | "b"            Alternation is frozenset({"a", "b"})
      "a"?                 Option is tuple ("repeat", 0, 1, "a")
      "a"*                 Repeat is tuple ("repeat", 0, inf, "a")
      "a"+                 Repeat is tuple ("repeat", 1, inf, "a")

      # EOF                End of whole text stream is ("$",)
      # UPPERCASE rule     Returns substring, including whitespace and //comment rule

      /* BNF source can have C multiline comments */
    """

    def __init__(self, text: str):
        self.text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        self.i = 0
        
        self.try_take(r"\s+")
        self.expr = self.parse()
        self.take(";")
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
            item = self.parseRepeat()
            if item:
                items.append(item)
            else:
                return solo(items, ("concat", *items))

    def parseRepeat(self):
        e = self.parseSingle()
        if c := self.try_take("[+?*{]"):
            lo, hi = 0, math.inf
            if c == "+":
                lo = 1
            elif c == "?":
                hi = 1
            return ("repeat", lo, hi, e)
        return e

    # Rule names can contain '+' so if followed by a letter it's part of the name not a regex repeat.
    ident_reg = r"^((?:[\w-]|\+\w)+)(\([\w(),<≤/\+-]+\))?"

    def parseSingle(self):
        if self.try_take('"'):
            s = self.parseString()
            if not self.try_take(r"\.\.\."):
                return s
            self.take('"')
            e = self.parseString()
            return range(ord(s), ord(e) + 1)
        elif name := self.try_take(r'\w+'):
            return "rule", name
        elif self.try_take(r'<any char except "\\"">'):
            return ("diff", range(0, 0x10FFFF), '"')
        elif self.try_take(r"\("):
            parens = self.parse()
            self.take(r"\)")
            return parens
        else:
            return None

    def parseString(self):
        cs = []
        while not self.try_take('"'):
            if self.try_take(r"\\"):
                c = self.take()
                if c != '"':
                    raise ValueError("expected", '"', "got", c)
                cs.append(c)
            else:
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
        yield (s.strip() for s in def_str.split("→"))


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
                rule = Bnf(text)
            except Exception as e:
                raise ValueError(name) from e
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
