from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, overload

from app.config import CRAFTING_INTERPRETERS

type ReportErrCB = Callable[[int, str, str], None]


# https://craftinginterpreters.com/scanning.html#token-type
class TokenType(IntEnum):
    # Single-character tokens.
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    COMMA = auto()
    DOT = auto()
    MINUS = auto()
    PLUS = auto()
    SEMICOLON = auto()
    SLASH = auto()
    STAR = auto()

    # One or two character tokens.
    BANG = auto()
    BANG_EQUAL = auto()
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()

    # Literals.
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # Keywords.
    AND = auto()
    CLASS = auto()
    ELSE = auto()
    FALSE = auto()
    FUN = auto()
    FOR = auto()
    IF = auto()
    NIL = auto()
    OR = auto()
    PRINT = auto()
    RETURN = auto()
    SUPER = auto()
    THIS = auto()
    TRUE = auto()
    VAR = auto()
    WHILE = auto()

    EOF = auto()


char_tokens = {
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "-": TokenType.MINUS,
    "+": TokenType.PLUS,
    ";": TokenType.SEMICOLON,
    "*": TokenType.STAR,
}

char_equal_tokens = {
    "!": TokenType.BANG,
    "=": TokenType.EQUAL,
    "<": TokenType.LESS,
    ">": TokenType.GREATER,
}

keywords = {tt.name.lower(): tt for tt in TokenType if TokenType.AND <= tt <= TokenType.WHILE}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    # column: int
    literal: object

    def __str__(self):
        lit = self.literal if self.literal is not None else "null"
        return f"{self.type.name} {self.lexeme} {lit}"


class Scanner:
    """Lexes tokens"""

    def __init__(self, source: str, report: ReportErrCB):
        """Take report() with DI to avoid circular import"""
        self.source = source
        self.start = 0
        self.current = 0
        self.line = 1
        # self.column = 1
        self.report = report

    def peek(self):
        """Will return empty string if EOF"""
        try:
            return self.source[self.current]
        except IndexError:
            return ""

    def peek_next(self):
        try:
            return self.source[self.current + 1]
        except IndexError:
            return ""

    def pop(self):
        """The only way to move current"""
        c = self.peek()
        if c == "\n":
            self.line += 1
            # self.column = 1
            pass
        self.current += 1
        return c

    @overload
    def take(self, m: str) -> bool: ...
    @overload
    def take[T](self, m: Callable[[str], T | None]) -> T | None: ...
    def take(self, m):
        c = self.peek()
        if not c:  # EOF
            return False
        if v := c == m if isinstance(m, str) else m(c):
            self.pop()
            return v

    def take_many(self, m: str | Callable[[str], Any]):
        while self.take(m):
            pass

    def skip_until(self, m: str | Callable[[str], Any]):
        """Skips as many as needed until m is taken"""
        while not self.take(m):
            if not self.pop():
                return False
        return True

    def scan_tokens(self) -> list[Token]:
        """Returns list instead of lazy generate that won't have fired events"""
        tokens = []
        while True:
            t = self.scan_token()
            if not t:
                continue
            tokens.append(t)
            if t.type == TokenType.EOF:
                return tokens

    def scan_token(self) -> Token | None:
        """Unlike the book's scanToken, return 0 or 1 tokens"""
        self.start = self.current

        if self.current >= len(self.source):
            return self.make_token(TokenType.EOF)

        if t := self.take(char_tokens.get):
            return self.make_token(t)

        if t := self.take(char_equal_tokens.get):
            return self.make_token(TokenType(t + bool(self.take("="))))

        if self.take(str.isspace):
            return self.scan_token()

        if self.take(str.isdigit):
            return self.number()

        if self.take('"'):
            return self.string()

        if self.take("/"):
            if self.take("/"):
                self.skip_until("\n")
                return self.scan_token()
            return self.make_token(TokenType.SLASH)

        if self.take(str.isidentifier):
            return self.identifier()

        if CRAFTING_INTERPRETERS():
            self.error("Unexpected character.")
            self.pop()
        else:
            self.error(f"Unexpected character: {self.pop()}")
        return None

    def make_token(self, type: TokenType, literal=None):
        return Token(type, self.lexeme(), self.line, literal)

    def string(self):
        if not self.skip_until('"'):
            self.error("Unterminated string.")
            return None
        return self.make_token(TokenType.STRING, self.lexeme()[1:-1])

    def lexeme(self):
        return self.source[self.start : self.current]

    def number(self):
        self.take_many(str.isdigit)

        # Don't take the . if it's not followed by digit
        if self.peek() == "." and (follow := self.peek_next()) and follow.isdigit():
            self.pop()
            self.take_many(str.isdigit)
        return self.make_token(TokenType.NUMBER, float(self.lexeme()))

    def identifier(self):
        def under_alpha_num(c):
            return c.isalnum() or c == "_"

        self.take_many(under_alpha_num)

        if keyword := keywords.get(self.lexeme()):
            return self.make_token(keyword)
        return self.make_token(TokenType.IDENTIFIER)

    def error(self, message: str):
        self.report(self.line, "", message)
