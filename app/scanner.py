from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Callable, overload



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
    
@dataclass(frozen=True)
class Error:
    message: str
    line: int
    # column: int

    def __str__(self):
        return f"[line {self.line}] Error: {self.message}"


class Scanner:
    """Returns tokens and errors"""

    def __init__(self, source: str):
        self.source = source + "\n"  # Adding last newline means we don't have to check for EOF
        self.start = 0
        self.current = 0
        self.line = 1
        # self.column = 1
        self.has_error = False

    def peek(self):
        return self.source[self.current]

    def pop(self):
        """The only way to move current forward"""
        c = self.peek()
        if c == "\n":
            self.line += 1
            # self.column = 1
            pass
        self.current += 1
        return c

    @overload
    def match(self, m: str) -> bool: ...
    @overload
    def match[T](self, m: Callable[[str], T | None]) -> T | None: ...
    def match(self, m):
        c = self.peek()
        if v := c == m if isinstance(m, str) else m(c):
            self.pop()
            return v

    def match_until(self, m: str | Callable):
        while not self.match(m):
            self.pop()

    def scan_tokens(self):
        while True:
            yield (t := self.scan_token())
            if isinstance(t, Token) and t.type == TokenType.EOF:
                break

    def scan_token(self) -> Token | Error:
        """Unlike the book's scan_token, just return 1 token"""
        self.start = self.current

        if self.current >= len(self.source):
            return self.make_token(TokenType.EOF)

        if t := self.match(char_tokens.get):
            return self.make_token(t)

        if t := self.match(char_equal_tokens.get):
            return self.make_token(TokenType(t + bool(self.match("="))))

        if self.match(str.isspace):
            return self.scan_token()

        if self.match(str.isdigit):
            return self.number()

        if self.match('"'):
            return self.string()

        if self.match("/"):
            if self.match("/"):
                self.match_until("\n")
                return self.scan_token()
            return self.make_token(TokenType.SLASH)

        if self.match(str.isalpha):
            return self.identifier()

        return self.error(f"Unexpected character: {self.pop()}")

    def make_token(self, type: TokenType, literal=None):
        return Token(type, self.lexeme(), self.line, literal)

    def string(self):
        self.match_until('"')
        return self.make_token(TokenType.STRING, self.lexeme()[1:-1])

    def lexeme(self):
        return self.source[self.start : self.current]

    def number(self):
        self.match_until(str.isdigit)
        if self.match("."):
            if not self.match(str.isdigit):
                return self.error("Invalid number ending in .")
            self.match_until(str.isdigit)
        return self.make_token(TokenType.NUMBER, float(self.lexeme()))

    def identifier(self):
        self.match_until(lambda c: not c.isalnum())

        if keyword := keywords.get(self.lexeme()):
            return self.make_token(keyword)
        return self.make_token(TokenType.IDENTIFIER)
    
    def error(self, message: str):
        self.has_error = True
        return Error(message, self.line)
