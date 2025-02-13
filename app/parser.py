from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Tuple, override

from app.scanner import Token, TokenType, TokenType as TT


class Visitor[T](ABC):
    @abstractmethod
    def visit_binary(self, binary: "Binary") -> T:
        pass

    @abstractmethod
    def visit_grouping(self, grouping: "Grouping") -> T:
        pass

    @abstractmethod
    def visit_literal(self, literal: "Literal") -> T:
        pass

    @abstractmethod
    def visit_unary(self, unary: "Unary") -> T:
        pass


class Expr(ABC):
    def accept[T](self, visitor: Visitor[T]) -> T:
        """i.e. calls self.binary(self)"""
        subclass_name = self.__class__.__name__.lower()
        return getattr(visitor, f"visit_{subclass_name}")(self)


@dataclass(frozen=True)
class Binary(Expr):
    left: object
    operator: Token
    right: object

    # Don't need @override accept() because it's dynamically dispatched in parent class
    # def accept(self, visitor: Visitor):
    #     return visitor.binary(self)


@dataclass(frozen=True)
class Grouping(Expr):
    value: object


@dataclass(frozen=True)
class Literal(Expr):
    value: object


@dataclass(frozen=True)
class Unary(Expr):
    operator: Token
    right: object


class AstPrinter(Visitor[str]):
    def print(self, expr: Expr):
        return expr.accept(self)

    @override
    def visit_binary(self, binary: Binary):
        return self.parens(binary.operator.lexeme, binary.left, binary.right)

    @override
    def visit_grouping(self, grouping: Grouping):
        return self.parens("group", grouping.value)

    @override
    def visit_literal(self, literal: Literal):
        match v := literal.value:
            case bool():
                return str(v).lower()
            case None:
                return "nil"
            case _:
                return str(v)

    @override
    def visit_unary(self, unary: Unary):
        return self.parens(unary.operator.lexeme, unary.right)

    def parens(self, name, *exprs: Tuple[Expr]):
        return f"({name} {' '.join(e.accept(self) for e in exprs)})"


# TODO above generate these? move to another file??


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token], report: Callable):
        self.tokens = tokens
        self.current = 0
        self.report = report

    def parse(self):
        try:
            e = self.expression()
        except ParseError:
            return None
        if self.peek().type != TT.EOF:
            self.error(self.peek(), "Expected end of expression")  # don't raise here
        return e

    def peek(self):
        return self.tokens[self.current]

    def pop(self):
        """The only way to move current"""
        try:
            return self.peek()
        except IndexError:
            return None
        finally:
            self.current += 1

    def take(self, *types: TokenType):
        for t in types:
            if self.peek().type == t:
                return self.pop()

    def expression(self):
        return self.equality()

    def equality(self):
        return self.take_binary(self.comparison, TT.BANG_EQUAL, TT.EQUAL_EQUAL)

    def comparison(self):
        return self.take_binary(self.term, TT.GREATER, TT.GREATER_EQUAL, TT.LESS, TT.LESS_EQUAL)

    def term(self):
        return self.take_binary(self.factor, TT.MINUS, TT.PLUS)

    def factor(self):
        return self.take_binary(self.unary, TT.STAR, TT.SLASH)

    def unary(self):
        if op := self.take(TT.BANG, TT.MINUS):
            return Unary(op, self.unary())
        return self.primary()

    def take_binary(self, f, *types):
        e = f()
        while op := self.take(*types):
            e = Binary(e, op, f())
        return e

    def primary(self):
        if e := self.take(TT.NUMBER, TT.STRING, TT.NIL):
            return Literal(e.literal)

        if e := self.take(TT.TRUE, TT.FALSE):
            return Literal(e.type == TT.TRUE)

        if e := self.take(TT.LEFT_PAREN):
            expr = self.expression()
            if not self.take(TT.RIGHT_PAREN):
                raise self.error(e, "Expect ')' after expression")
            return Grouping(expr)

        raise self.error(self.peek(), "Expect expression")

    def error(self, token: Token, message: str):
        lexeme = f"'{token.lexeme}'" if token.type != TT.EOF else "end"

        self.report(token.line, f" at {lexeme}", message)
        return ParseError()


if __name__ == "__main__":
    expr = Binary(
        Unary(Token(TT.MINUS, "-", 1, None), Literal(123)),
        Token(TT.STAR, "*", 1, None),
        Grouping(Literal(45.67)),
    )
    print(AstPrinter().print(expr))
