from app.parser import Parser
from app.scanner import Scanner, TokenType


def reraise(e, *other):
    if isinstance(e, Exception):
        raise AssertionError from e
    raise AssertionError(e, *other)


def parse_for_errors(source, reporter):
    """Hacky workaround to parse either. Can produce errors"""
    tokens = Scanner(source, reporter).scan_tokens()
    parser = Parser(source, reporter)

    # Might regret this magic, so don't move this to app/
    if any(t.type in (TokenType.SEMICOLON, TokenType.LEFT_BRACE) for t in tokens): # TODO switch to bnf_scanner
        return parser.parse_stmt()
    return parser.parse_expr()


def parse(source):
    """Hacky workaround to parse either. Raises on compile errors"""
    if e := parse_for_errors(source, reraise):
        return e
    raise AssertionError("parse_expr returned which is impossible because of reraise")  # pragma: no cover
