from typing import Callable

from app.ast import AstPrinter
from app.expression import Binary, Grouping, Literal, Unary
from app.scanner import Token, TokenType, TokenType as TT
from app.statement import Expression, Print


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token], report: Callable):
        self.tokens = tokens
        self.current = 0
        self.report = report

    def parse_stmt(self):
        statements = []
        while not self.at_end():
            if st := self.declaration():
                statements.append(st)
            # MAYBE: else should list really have None?
        return statements

    def parse_expr(self):
        try:
            e = self.expression()
        except ParseError:
            return None
        if not self.at_end():
            self.error(self.peek(), "Expected end of expression")  # don't raise here
        return e

    def at_end(self):
        return self.peek().type == TT.EOF

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

    def try_take(self, *types: TokenType):
        for t in types:
            if self.peek().type == t:
                return self.pop()

    def take(self, message, *types: TokenType):
        if not (t := self.try_take(*types)):
            raise self.error(self.peek(), message)
        return t

    """
        https://craftinginterpreters.com/appendix-i.html

        Statement Grammar

program        → declaration* EOF ;
declaration    → statement ;
statement      → exprStmt
               | printStmt ;
exprStmt       → expression ";" ;
printStmt      → "print" expression ";" ;
    """

    def declaration(self):
        try:
            # TODO VAR
            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def statement(self):
        if self.try_take(TT.PRINT):
            st = Print(self.expression())
            self.take("Expect ';' after value.", TT.SEMICOLON)
            return st
        st = Expression(self.expression())
        self.take("Expect ';' after expression.", TT.SEMICOLON)
        return st

    """
        Expression Grammar

expression     → equality ;
equality       → comparison ( ( "!=" | "==" ) comparison )* ;
comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )* ;
term           → factor ( ( "-" | "+" ) factor )* ;
factor         → unary ( ( "/" | "*" ) unary )* ;
unary          → ( "!" | "-" ) unary
               | primary ;
primary        → NUMBER | STRING | "true" | "false" | "nil"
               | "(" expression ")" ;
    """

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
        if op := self.try_take(TT.BANG, TT.MINUS):
            return Unary(op, self.unary())
        return self.primary()

    def take_binary(self, f, *types):
        e = f()
        while op := self.try_take(*types):
            e = Binary(e, op, f())
        return e

    def primary(self):
        if e := self.try_take(TT.NUMBER, TT.STRING, TT.NIL):
            return Literal(e.literal)

        if e := self.try_take(TT.TRUE, TT.FALSE):
            return Literal(e.type == TT.TRUE)

        if e := self.try_take(TT.LEFT_PAREN):
            expr = self.expression()
            self.take("Expect ')' after expression", TT.RIGHT_PAREN)
            return Grouping(expr)

        raise self.error(self.peek(), "Expect expression")

    ### Error Handling ###
    def synchronize(self):
        """Stop after semicolon or before next statement"""
        while not self.at_end():
            if self.try_take(TT.SEMICOLON):
                return
            match self.pop().type:
                case TT.CLASS | TT.FUN | TT.VAR | TT.FOR | TT.IF | TT.WHILE | TT.PRINT | TT.RETURN:
                    return

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

    print(AstPrinter().print(Expression(expr)))
    print(AstPrinter().print(Print(expr)))
