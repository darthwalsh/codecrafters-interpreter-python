from collections.abc import Callable
from contextlib import contextmanager

from app.expression import Assign, Binary, Call, Expr, Grouping, Literal, Logical, Unary, Variable
from app.scanner import Token, char_tokens
from app.scanner import TokenType as TT
from app.statement import Block, Expression, Function, If, Print, Return, Stmt, Var, While


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token], report: Callable[[int, str, str], None]):
        self.tokens = tokens
        self.current = 0
        self.report = report

    def parse_stmt(self):
        statements: list[Stmt] = []
        while not self.at_end():
            if st := self.declaration():
                statements.append(st)
            # MAYBE: else should list really have None?
        return statements

    def parse_expr(self) -> Expr | None:
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
        finally:
            self.current += 1

    def try_take(self, *types: TT):
        for t in types:
            if self.peek().type == t:
                return self.pop()

    def take(self, t: TT, message: str):
        if to := self.try_take(t):
            return to
        raise self.error(self.peek(), message)

    def expect(self, t: TT, *, after: str):
        return self.take(t, f"Expect '{Parser.token_type_2_char[t]}' after {after}")

    token_type_2_char = {v: k for k, v in char_tokens.items()}

    @contextmanager
    def followed_by(self, t: TT, *, after: str):
        yield
        self.take(t, f"Expect '{Parser.token_type_2_char[t]}' after {after}")

    """
        https://craftinginterpreters.com/appendix-i.html

        Statement Grammar

program        → declaration* EOF ;
declaration    → funDecl
               | varDecl
               | statement ;

funDecl        → "fun" function ;
function       → IDENTIFIER "(" parameters? ")" block ;
parameters     → IDENTIFIER ( "," IDENTIFIER )* ;

varDecl        → "var" IDENTIFIER ( "=" expression )? ";" ;
statement      → exprStmt
               | forStmt
               | ifStmt
               | printStmt
               | returnStmt
               | whileStmt
               | block ;
exprStmt       → expression ";" ;
forStmt        → "for" "(" ( varDecl | exprStmt | ";" )
                 expression? ";"
                 expression? ")" statement ;
ifStmt         → "if" "(" expression ")" statement
               ( "else" statement )? ;
printStmt      → "print" expression ";" ;
returnStmt     → "return" expression? ";" ;
whileStmt      → "while" "(" expression ")" statement ;
block          → "{" declaration* "}" ;
    """

    def declaration(self) -> Stmt | None:
        try:
            if self.try_take(TT.FUN):
                return self.fun("function")
            if self.try_take(TT.VAR):
                return self.var_declaration()
            return self.statement()
        except ParseError:
            self.synchronize()
            return None

    def fun(self, kind):
        name = self.take(TT.IDENTIFIER, f"Expect {kind} name.")
        self.expect(TT.LEFT_PAREN, after=f"{kind} name.")

        params = []
        if not self.try_take(TT.RIGHT_PAREN):
            params.append(self.take(TT.IDENTIFIER, "Expect parameter name."))
            while self.try_take(TT.COMMA):
                params.append(self.take(TT.IDENTIFIER, "Expect parameter name."))
            self.expect(TT.RIGHT_PAREN, after="parameters.")

        self.take(TT.LEFT_BRACE, f"Expect '{{' before {kind} body.")
        return Function(name, params, self.block())

    def var_declaration(self):
        name = self.take(TT.IDENTIFIER, "Expect variable name.")
        with self.followed_by(TT.SEMICOLON, after="variable declaration."):
            if self.try_take(TT.EQUAL):
                return Var(name, self.expression())
            return Var(name, None)

    def statement(self):
        if self.try_take(TT.FOR):
            return self.for_statement()

        if self.try_take(TT.PRINT):
            with self.followed_by(TT.SEMICOLON, after="value."):
                return Print(self.expression())

        if self.try_take(TT.IF):
            self.expect(TT.LEFT_PAREN, after="'if'.")
            condition = self.expression()
            self.expect(TT.RIGHT_PAREN, after="condition.")
            then_branch = self.statement()
            else_branch = None
            if self.try_take(TT.ELSE):
                else_branch = self.statement()
            return If(condition, then_branch, else_branch)

        if ret := self.try_take(TT.RETURN):
            if self.try_take(TT.SEMICOLON):
                return Return(ret, None)
            with self.followed_by(TT.SEMICOLON, after="return value."):
                return Return(ret, self.expression())

        if self.try_take(TT.WHILE):
            self.expect(TT.LEFT_PAREN, after="'while'.")
            condition = self.expression()
            self.expect(TT.RIGHT_PAREN, after="condition.")
            body = self.statement()
            return While(condition, body)

        if self.try_take(TT.LEFT_BRACE):
            return Block(self.block())
        return self.expression_statement()

    def expression_statement(self):
        with self.followed_by(TT.SEMICOLON, after="expression."):
            return Expression(self.expression())

    def for_statement(self):
        self.expect(TT.LEFT_PAREN, after="'for'.")

        initializer = None
        if self.try_take(TT.SEMICOLON):
            pass
        elif self.try_take(TT.VAR):
            initializer = self.var_declaration()
        else:
            initializer = self.expression_statement()

        if self.try_take(TT.SEMICOLON):
            condition = None
        else:
            condition = self.expression()
            self.expect(TT.SEMICOLON, after="loop condition.")

        if self.try_take(TT.RIGHT_PAREN):
            increment = None
        else:
            increment = self.expression()
            self.expect(TT.RIGHT_PAREN, after="for clauses.")

        body = self.statement()

        if increment:
            body = Block([body, Expression(increment)])

        if condition is None:
            condition = Literal(True)

        body = While(condition, body)

        if initializer:
            body = Block([initializer, body])

        return body

    def block(self):
        statements = []
        while not self.try_take(TT.RIGHT_BRACE):
            if self.at_end():
                raise self.error(self.peek(), "Expect '}' after block.")

            if st := self.declaration():
                statements.append(st)
        return statements

    """
        Expression Grammar

expression     → assignment ;
assignment     → IDENTIFIER "=" assignment
               | logic_or ;
logic_or       → logic_and ( "or" logic_and )* ;
logic_and      → equality ( "and" equality )* ;
equality       → comparison ( ( "!=" | "==" ) comparison )* ;
comparison     → term ( ( ">" | ">=" | "<" | "<=" ) term )* ;
term           → factor ( ( "-" | "+" ) factor )* ;
factor         → unary ( ( "/" | "*" ) unary )* ;
unary          → ( "!" | "-" ) unary | call ;
call           → primary ( "(" arguments? ")" )* ;
arguments      → expression ( "," expression )* ;
primary        → NUMBER | STRING | "true" | "false" | "nil"
               | "(" expression ")"
               | IDENTIFIER ;
    """

    def expression(self) -> Expr:
        return self.assignment()

    def assignment(self):
        name = self.logic_or()

        if eq := self.try_take(TT.EQUAL):
            value = self.assignment()

            if isinstance(name, Variable):
                return Assign(name.name, value)

            self.error(eq, "Invalid assignment target.")  # don't raise, can return

        return name

    def logic_or(self):
        return self.take_binary(self.logic_and, TT.OR, tt=Logical)

    def logic_and(self):
        return self.take_binary(self.equality, TT.AND, tt=Logical)

    def equality(self):
        return self.take_binary(self.comparison, TT.BANG_EQUAL, TT.EQUAL_EQUAL)

    def comparison(self):
        return self.take_binary(self.term, TT.GREATER, TT.GREATER_EQUAL, TT.LESS, TT.LESS_EQUAL)

    def term(self):
        return self.take_binary(self.factor, TT.MINUS, TT.PLUS)

    def factor(self):
        return self.take_binary(self.unary, TT.STAR, TT.SLASH)

    def take_binary(self, take_expr: Callable[[], Expr], *types, tt: type[Logical] | type[Binary] = Binary):
        e = take_expr()
        while op := self.try_take(*types):
            e = tt(e, op, take_expr())
        return e

    def unary(self):
        if op := self.try_take(TT.BANG, TT.MINUS):
            return Unary(op, self.unary())
        return self.call()

    def call(self):
        e = self.primary()
        while self.try_take(TT.LEFT_PAREN):
            e = self.finish_call(e)
        return e

    def finish_call(self, callee):
        if p := self.try_take(TT.RIGHT_PAREN):
            return Call(callee, p, [])

        args = [self.expression()]
        while self.try_take(TT.COMMA):
            if len(args) >= 255:
                self.error(self.peek(), "Can't have more than 255 arguments.")
            args.append(self.expression())
        p = self.expect(TT.RIGHT_PAREN, after="arguments.")
        return Call(callee, p, args)

    def primary(self):
        if e := self.try_take(TT.NUMBER, TT.STRING, TT.NIL):
            return Literal(e.literal)

        if e := self.try_take(TT.TRUE, TT.FALSE):
            return Literal(e.type == TT.TRUE)

        if e := self.try_take(TT.LEFT_PAREN):
            with self.followed_by(TT.RIGHT_PAREN, after="expression"):
                return Grouping(self.expression())

        if e := self.try_take(TT.IDENTIFIER):
            return Variable(e)

        raise self.error(self.peek(), "Expect expression")

    ### Error Handling ###
    def synchronize(self):
        """Stop after semicolon or before next statement"""
        while not self.at_end():
            if self.try_take(TT.SEMICOLON):
                return
            if self.peek().type in (TT.CLASS, TT.FUN, TT.VAR, TT.FOR, TT.IF, TT.WHILE, TT.PRINT, TT.RETURN):
                return
            self.pop()

    def error(self, token: Token, message: str):
        lexeme = f"'{token.lexeme}'" if token.type != TT.EOF else "end"

        self.report(token.line, f" at {lexeme}", message)
        return ParseError()
