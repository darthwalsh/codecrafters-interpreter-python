import math
import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
import typing

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
        elif name := self.try_take(r"\w+"):
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
class Parse:
    rule: str
    start: int
    end: int
    expr: object

    def __iter__(self):
        yield self.rule
        yield self.start
        yield self.end
        yield self.expr

    def __str__(self):
        match self.rule:
            case "IDENTIFIER": return f"_{self.expr}"
            case "STRING": return repr(self.expr)
            case "NUMBER":return f"+{self.expr}"
            case "DIGIT": return f"d{self.expr}"
            case "EOF": return "<eof>"
            case _: pass
        if self.rule.isupper():
            raise ValueError(self.expr)

        if isinstance(self.expr, tuple):
            expr = ", ".join(map(str, self.expr))
        else:
            expr = str(self.expr)
        return f"{self.rule}({expr})"

    def __repr__(self):
        return str(self)


def untuple(o: object): # TODO delete??
    if isinstance(o, tuple):
        result = []
        for t in o:
            t = untuple(t)
            if t != ():
                result.append(t)
        if len(result) == 1:
            return result[0]
        return tuple(result)
    if isinstance(o, Parse):
        if o.rule.startswith("_"):
            return untuple(o.expr)
        return replace(o, expr=untuple(o.expr))
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
            if name in self.bnf:
                raise ValueError("duplicate", name)
            self.bnf[name] = rule.expr
        self.bnf["EOF"] = ("$",)

    def parse(self, text: str, expr):
        self.text = text

        results: set[Parse] = set()  # TODO don't need set?? Just take the first of ordered frozenset?
        for result in self.resolve(0, expr, skip_ws=True):
            if self.ignore_whitespace(result.end) == len(text):
                results.add(result)

        if not results:
            raise ValueError("no results")
        if len(results) != 1:
            raise ValueError("ambiguous", results)
        return next(iter(results))

    def ignore_whitespace(self, i: int) -> int:
        if i + 1 < len(self.text) and self.text[i : i + 2] == "//":
            try:
                return self.ignore_whitespace(1 + self.text.index("\n", i))
            except ValueError:
                return len(self.text)
        if i < len(self.text) and self.text[i].isspace():
            return self.ignore_whitespace(i + 1)
        return i

    def resolve(self, i: int, expr, skip_ws) -> Iterator[Parse]:
        """Produces a very verbose parse tree, but simple is better than clever. Let another layer figure out the AST."""
        if skip_ws:
            i = self.ignore_whitespace(i)
        match expr:
            case str(s):
                if i < len(self.text) and self.text[i : i + len(s)] == s:
                    yield Parse("_str", i, i + len(s), s)
            case range():
                if i < len(self.text) and ord(self.text[i]) in expr:
                    yield Parse("_range", i, i + 1, self.text[i])
            case set() | frozenset():
                for e in expr:
                    yield from self.resolve(i, e, skip_ws)
            case ("concat",):
                yield Parse("_concat", i, i, ())
            case ("concat", e, *exprs):
                for head in self.resolve(i, e, skip_ws):
                    for tail in self.resolve(head.end, ("concat", *exprs), skip_ws):
                        combined = (head,) + typing.cast(tuple[object, ...], tail.expr) if head.expr else tail.expr
                        yield Parse("_concat", head.start, tail.end, combined)
            case ("repeat", lo, hi, e):
                if not lo:
                    yield Parse("_repeat", i, i, ())
                if hi:
                    dec = ("repeat", max(lo - 1, 0), hi - 1, e)
                    for head in self.resolve(i, e, skip_ws):
                        for tail in self.resolve(head.end, dec, skip_ws):
                            combined = (head,) + typing.cast(tuple[object, ...], tail.expr) if head.expr else tail.expr
                            yield Parse("_repeat", head.start, tail.end, combined)
            case ("rule", name):
                definition = self.bnf[name]
                literal_text = name.isupper()
                for e in self.resolve(i, definition, skip_ws=not literal_text):
                    if literal_text:
                        # Throw away parse tree
                        yield Parse(name, e.start, e.end, self.text[e.start : e.end])
                    else:
                        yield Parse(name, e.start, e.end, e)
                        # yield replace(e, expr=untuple(e.expr))
                        # yield untuple(e)
                    # elif isinstance(e, Parse):
                    #     yield e, ii
                    # else:
                    #     yield Parse(name, i, ii, e), ii
            case ("diff", e, *subtrahends):
                for s in subtrahends:
                    for _ in self.resolve(i, s, skip_ws):
                        return
                # TODO this duplicates above??
                if not any(any(self.resolve(i, s, skip_ws)) for s in subtrahends):  
                    yield from self.resolve(i, e, skip_ws)
            case ("$",):
                if i == len(self.text):
                    yield Parse("_EOF", i, i, ())
            case _:
                raise ValueError("unknown type:", expr)
