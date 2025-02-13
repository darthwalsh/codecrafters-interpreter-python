from app.expression import Expr
from app.parser import Parser
from app.scanner import Scanner
from app.statement import Stmt


errors = []


def _report(_line, _where, message):
    errors.append(message)


def scan_tokens(source):
    errors.clear()
    scanner = Scanner(source, _report)
    return scanner.scan_tokens()


def parse_expr(source):
    errors.clear()
    tokens = Scanner(source, _report).scan_tokens()
    if errors:
        return None
    return Parser(tokens, _report).parse_expr() if not errors else None


def parse_stmt(source):
    errors.clear()
    tokens = Scanner(source, _report).scan_tokens()
    if errors:
        return None
    return Parser(tokens, _report).parse_stmt()


def parse(source) -> Expr | list[Stmt]:
    """Hacky workaround to parse either. Asserts no errors"""
    try:
        if ";" in source:  # Might regret this later, so don't move this to app
            return parse_stmt(source)
        return parse_expr(source)
    finally:
        if errors:
            raise AssertionError("Parse/Lex error:", errors)
