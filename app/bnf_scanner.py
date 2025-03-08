import logging
import typing
from collections.abc import Callable
from functools import cache

from app.bnf_lib import Ast, Bnf, Lib, Parse
from app.parser import all_tokens


class Walker:
    """Walks the BNF to find all terminal text as a token"""

    def __init__(self):
        self.found: set[str] = set()

    def resolve(self, expr):
        match expr:
            case str(s):
                self.found.add(s)
            case range():
                pass
            case list():
                for e in expr:
                    self.resolve(e)
            case ("repeat", _, _, e):
                self.resolve(e)
            case ("rule", _name):
                pass
            case (_kind, *sub):
                for e in sub:
                    self.resolve(e)
            case _:
                raise RuntimeError("Impossible state:", expr)


@cache
def bnf_tokens():
    token_lib = Lib.full()
    walker = Walker()
    for name, expr in token_lib.bnf.items():
        if not name.isupper():
            walker.resolve(expr)

    return frozenset(walker.found)
    # MAYBE after moving __main__ code to unittest, make app.parser use bnf_tokens not all_tokens? But it's not a map to TokenType strings i.e. BANG_EQUAL


class Scanner:
    """Lexes tokens"""

    def __init__(self, source: str, report: Callable[[int, str, str], None]):
        """Take report() with DI to avoid circular import"""
        self.source = source

        self.lib = Lib.full()  # MAYBE split out the rules to just parse uppercase?
        self.lib.bnf["KEYWORD"] = sorted(bnf_tokens())

        # MAYBE(first) could remove this workaround, which ensures that long text/numbers are not split up into ambiguous parse
        b = "(KEYWORD | STRING | IDENTIFIER KEYWORD | NUMBER KEYWORD)* (IDENTIFIER | NUMBER)? EOF ;"
        # TODO(token) this hack still doesn't work: `for (; ; ) 1;` is ambiguous parse, either FOR but also as IDENTIFIER(f) then OR
        self.lib.bnf["tokens"] = Bnf(b).expr

        self.report = report

    # TODO(token) returning list[Parse] doesn't render right in tokenize output, need to make Token
    def scan_tokens(self) -> list[Parse]:
        tokens = self.lib.parse(self.source, ("rule", "tokens"))
        logging.info(tokens)

        result = []
        repeat, final, eof = typing.cast(tuple[Ast, ...], typing.cast(Parse, tokens).expr)
        for token in typing.cast(tuple[Ast, ...], repeat):
            if isinstance(token, tuple):
                result.extend(token)
            else:
                result.append(token)
        if final:
            result.append(final)
        result.append(eof)
        return result


if __name__ == "__main__":
    walked = bnf_tokens()
    in_future_chapter = ". class super this".split()
    print(*sorted(walked | set(in_future_chapter)))
    print(*sorted(set(all_tokens)))
