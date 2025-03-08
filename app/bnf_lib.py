import logging
import math
import re
import typing
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from app.scanner import keywords

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
      "a" "b"              Concatenation is tuple ("concat", "a", "b")
      "a" | "b"            Alternation is list ["a", "b"]
      "a"?                 Option is tuple ("optional", "a")
      "a"*                 Repeat is tuple ("repeat", 0, inf, "a")
      "a"+                 Repeat is tuple ("repeat", 1, inf, "a")
      <any char except "\""> ("non_double_quote",)

      # EOF                End of whole text stream is ("EOF",)
      # UPPERCASE rule     Returns substring, including whitespace and //comment rule
      # IDENTIFIER         has special case, not to return reserved words. In theory, could add rules to BNF:
                           ALPHA ( ALPHA | DIGIT )* - "nil" - "true" - "return" ... etc but seems too messy

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
        items = []
        while True:
            items.append(self.parseConcat())
            if not self.try_take(r"\|"):
                return solo(items)

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
        if c := self.try_take(r"\?"):
            return ("optional", e)
        if c := self.try_take(r"[+*]"):
            lo = 1 if c == "+" else 0
            return ("repeat", lo, math.inf, e)
        return e

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
            return ("non_double_quote",)
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

    def try_take(self, pattern=".") -> str | None:
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


type Ast = str | None | Parse | tuple[Ast, ...]


@dataclass(frozen=True)
class Parse:
    rule: str
    expr: Ast

    def __str__(self):
        match self.rule:
            case "IDENTIFIER":
                return f"_{self.expr}"
            case "STRING":
                return typing.cast(str, self.expr)
            case "NUMBER":
                return f"+{self.expr}"
            case "DIGIT":
                return f"d{self.expr}"
            case "KEYWORD":  # HACK, should document this
                return f"`{self.expr}`"
            case "EOF":
                return "<eof>"
            case _:
                pass
        if self.rule.isupper():
            raise RuntimeError("Impossible state:", self.expr)  # pragma: no cover

        if isinstance(self.expr, tuple):
            expr = ", ".join(map(str, self.expr))
        else:
            expr = str(self.expr)
        return f"{self.rule}({expr})"

    def __repr__(self):
        return str(self)


def de_tree(tree: Ast) -> Ast:
    """Remove unnecessary Parse Tree nodes: have a single-item tuple expr, or Parse node child"""
    match tree:
        case Parse(_, p) if isinstance(p, Parse):
            return de_tree(p)
        case Parse(_, (solo,)):
            return de_tree(solo)
        case Parse(_, expr):
            return replace(tree, expr=de_tree(expr))
        case tuple():
            return tuple(de_tree(e) for e in tree)
        case _:
            return tree


class Lib:
    def __init__(self):
        self.bnf = {}

    @staticmethod
    def full():
        lib = Lib()
        lib.load_defs()
        return lib

    def load_defs(self):
        self.load_rules(self.read_productions())
        self.bnf["EOF"] = ("EOF",)

    def read_productions(self):
        productions_path = (Path(__file__).parent / "productions.bnf").resolve()
        with open(productions_path, encoding="utf-8") as f:
            productions = f.read()
        return productions

    def load_rules(self, productions):
        for name, text in split_defs(productions):
            try:
                rule = Bnf(text)
            except Exception as e:
                raise ValueError(name) from e
            if name in self.bnf:
                raise ValueError("duplicate", name)
            self.bnf[name] = rule.expr

    def parse(self, text: str, expr):
        self.text = text

        result = None
        for r, end in self.resolve(0, expr, skip_ws=True):
            if self.ignore_whitespace(end) == len(text):
                if result:
                    raise ValueError("ambiguous", result, r)
                result = r

        if result is None:
            raise ValueError("no results")
        return result

    def ignore_whitespace(self, i: int) -> int:
        if i + 1 < len(self.text) and self.text[i : i + 2] == "//":
            try:
                return self.ignore_whitespace(1 + self.text.index("\n", i))
            except ValueError:
                return len(self.text)
        if i < len(self.text) and self.text[i].isspace():
            return self.ignore_whitespace(i + 1)
        return i

    def resolve(self, i: int, expr, skip_ws) -> Iterator[tuple[Ast, int]]:
        """Produces the full parse tree with single-element productions, but simple is better than clever.
        Let another layer figure out the AST.


        MAYBE(first) just return the first found object -- IF backtracking not needed, then can have self.i move forward.

        Returns AST:
            - "abc" "" - str for str and range
            - (e1,e2) (e1,) () - tuples for concat and repeat
            - e1 None - None or the value for optional
            - Parse("rule", ..., name) rule creates Parse: MAYBE could return a simpler data structure? see split_parse_result but don't literally use tuples, confusing with above
            - () for EOF

        Tried a version of this code that produced Parse instead of tuple[object, int].
        Definitely should not flatten ((a, b), c) to (a, b, c) because that will end up losing the tree structure.
        """
        if skip_ws:
            i = self.ignore_whitespace(i)
        logging.debug("resolve(%s %s", i, expr)
        match expr:
            case str(s):
                if i < len(self.text) and self.text[i : i + len(s)] == s:
                    yield s, i + len(s)
            case range():
                if i < len(self.text) and ord(self.text[i]) in expr:
                    yield self.text[i], i + 1
            case list():
                for e in expr:
                    yield from self.resolve(i, e, skip_ws)
            case ("concat",):
                yield (), i
            case ("concat", e, *exprs):
                for vv, ii in self.resolve(i, e, skip_ws):
                    for vvv, iii in self.resolve(ii, ("concat", *exprs), skip_ws):
                        combined = (vv,) + typing.cast(tuple[Ast, ...], vvv) if vv != () else vvv
                        yield combined, iii
            case ("optional", e):
                yield None, i
                yield from self.resolve(i, e, skip_ws)
            case ("repeat", lo, hi, e):
                if not lo:
                    yield (), i
                if hi:
                    dec = ("repeat", max(lo - 1, 0), hi - 1, e)
                    for vv, ii in self.resolve(i, e, skip_ws):
                        for vvv, iii in self.resolve(ii, dec, skip_ws):
                            combined = (vv,) + typing.cast(tuple[Ast, ...], vvv) if vv != () else vvv
                            yield combined, iii
            case ("rule", name):
                literal_text = name.isupper()
                for e, ii in self.resolve(i, self.bnf[name], skip_ws=not literal_text):
                    # Throw away parse tree for UPPERCASE rule
                    subtree = self.text[i:ii] if literal_text else e
                    # documented HACK for IDENTIFIER, otherwise `return;` is ambiguous parse for Expression(Var("return"))
                    if name == "IDENTIFIER" and subtree in keywords:
                        continue
                    yield Parse(name, subtree), ii
            case ("non_double_quote",):
                if i < len(self.text) and self.text[i] != '"':
                    yield self.text[i], i + 1
            case ("EOF",):
                if i == len(self.text):
                    yield (), i
            case _:
                raise RuntimeError("Impossible state:", expr)
