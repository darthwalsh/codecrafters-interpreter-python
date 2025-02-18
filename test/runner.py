from app.expression import Expr
from app.parser import Parser
from app.scanner import Scanner
from app.statement import Stmt


errors = []  # HACK useful to have global, but maybe make parse_* below return new errors list


def scan_tokens(source, reporter):
    scanner = Scanner(source, reporter)
    return scanner.scan_tokens()


def parse_expr(source, reporter):
    tokens = scan_tokens(source, reporter)
    return Parser(tokens, reporter).parse_expr()


def parse_stmt(source, reporter):
    tokens = scan_tokens(source, reporter)
    return Parser(tokens, reporter).parse_stmt()


def parse(source, reporter) -> Expr | list[Stmt]:
    """Hacky workaround to parse either. Asserts no errors"""
    if ";" in source or "{" in source:  # Might regret this later, so don't move this to app/
        return parse_stmt(source, reporter)
    return parse_expr(source, reporter)


def reraise(e, *other):
    if isinstance(e, Exception):
        raise AssertionError from e
    raise AssertionError(e, *other)
