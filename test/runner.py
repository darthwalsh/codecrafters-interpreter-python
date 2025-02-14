from app.expression import Expr
from app.parser import Parser
from app.scanner import Scanner
from app.statement import Stmt


errors = []  # HACK useful to have global, but maybe make parse_* below return new errors list


def _report(_line, _where, message):
    errors.append(message)


def scan_tokens(source):
    errors.clear()
    scanner = Scanner(source, _report)
    return scanner.scan_tokens()


def parse_expr(source, reporter=_report):
    errors.clear()
    tokens = Scanner(source, reporter).scan_tokens()
    if errors:
        return None
    return Parser(tokens, reporter).parse_expr() if not errors else None


def parse_stmt(source, reporter=_report):
    errors.clear()
    tokens = Scanner(source, reporter).scan_tokens()
    if errors:
        return None
    return Parser(tokens, reporter).parse_stmt()


def parse(source, reporter=_report) -> Expr | list[Stmt]:
    """Hacky workaround to parse either. Asserts no errors"""
    try:
        if ";" in source or "{" in source:  # Might regret this later, so don't move this to app
            return parse_stmt(source, reporter)
        return parse_expr(source, reporter)
    finally:
        if errors:
            raise AssertionError("Parse/Lex error:", errors)


def reraise(e, *other):
    if isinstance(e, Exception):
        raise AssertionError from e
    raise AssertionError(e, *other)
