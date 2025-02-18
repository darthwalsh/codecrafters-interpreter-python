from app.expression import Expr
from app.parser import Parser
from app.scanner import Scanner, TokenType
from app.statement import Stmt


def parse_expr(source, reporter):
    tokens = Scanner(source, reporter).scan_tokens()
    return Parser(tokens, reporter).parse_expr()


def parse_stmt(source, reporter):
    tokens = Scanner(source, reporter).scan_tokens()
    return Parser(tokens, reporter).parse_stmt()


def parse(source) -> Expr | list[Stmt]:
    """Hacky workaround to parse either. Raises on compile errors"""
    tokens = Scanner(source, reraise).scan_tokens()
    parser = Parser(tokens, reraise)

    # Might regret this magic, so don't move this to app/
    if any(t.type in (TokenType.SEMICOLON, TokenType.LEFT_BRACE) for t in tokens):
        return parser.parse_stmt()
    return parser.parse_expr()


def reraise(e, *other):
    if isinstance(e, Exception):
        raise AssertionError from e
    raise AssertionError(e, *other)
