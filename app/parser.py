from typing import Callable

from app.expression import Assign, Binary, Grouping, Literal, Unary, Variable
from app.scanner import Token, TokenType as TT
from app.statement import Block, Expression, Print, Var


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

    def try_take(self, *types: TT):
        for t in types:
            if self.peek().type == t:
                return self.pop()

    def take(self, message, *types: TT):
        if not (t := self.try_take(*types)):
            raise self.error(self.peek(), message)
        return t

    """
        https://craftinginterpreters.com/appendix-i.html

        Statement Grammar

program        → declaration* EOF ;
declaration    → varDecl
               | statement ;
varDecl        → "var" IDENTIFIER ( "=" expression )? ";" ;
statement      → exprStmt
               | printStmt
               | block ;
exprStmt       → expression ";" ;
printStmt      → "print" expression ";" ;
block          → "{" declaration* "}" ;
    """

    def declaration(self):
        try:
            if self.try_take(TT.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def var_declaration(self):
        name = self.take("Expect variable name.", TT.IDENTIFIER)
        initializer = None
        if self.try_take(TT.EQUAL):
            initializer = self.expression()
        self.take("Expect ';' after variable declaration.", TT.SEMICOLON)
        return Var(name, initializer)

    def statement(self):
        if self.try_take(TT.PRINT):
            st = Print(self.expression())
            self.take("Expect ';' after value.", TT.SEMICOLON)
            return st
        if self.try_take(TT.LEFT_BRACE):
            return Block(self.block())
        st = Expression(self.expression())
        self.take("Expect ';' after expression.", TT.SEMICOLON)
        return st
    
    def block(self):
        statements = []
        while not self.try_take(TT.RIGHT_BRACE):
            if self.at_end():
                raise self.error(self.peek(), "Expect '}' after block.")
                break

            if st := self.declaration():
                statements.append(st)
        return statements

    """
        Expression Grammar

expression     → assignment ;
assignment     → IDENTIFIER "=" assignment
               | equality ;
equality       → comparison ( ( "!=" | "==" ) comparison )* ;
comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )* ;
term           → factor ( ( "-" | "+" ) factor )* ;
factor         → unary ( ( "/" | "*" ) unary )* ;
unary          → ( "!" | "-" ) unary
               | primary ;
primary        → NUMBER | STRING | "true" | "false" | "nil"
               | "(" expression ")"
               | IDENTIFIER ;
    """

    def expression(self):
        return self.assignment()
    
    def assignment(self):
        name = self.equality()

        if eq := self.try_take(TT.EQUAL):
            value = self.assignment()

            if isinstance(name, Variable):
                return Assign(name.name, value)
            
            self.error(eq, "Invalid assignment target.")  # don't raise, can return
        
        return name


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
        
        if e := self.try_take(TT.IDENTIFIER):
            return Variable(e)

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
