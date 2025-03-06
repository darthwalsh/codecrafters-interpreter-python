import logging
import typing
from collections.abc import Callable
from contextlib import contextmanager

from app.bnf_lib import Lib, Parse, de_tree
from app.expression import Assign, Binary, Call, Expr, Grouping, Literal, Logical, Unary, Variable
from app.scanner import Token, char_equal_tokens, char_tokens, keywords
from app.scanner import TokenType as TT
from app.statement import Block, Expression, Function, If, Print, Return, Stmt, Var, While


class ParseError(Exception):
    pass


class OldParser:  # TODO(cleanup)
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
        return self.take(t, f"Expect '{OldParser.token_type_2_char[t]}' after {after}")

    token_type_2_char = {v: k for k, v in char_tokens.items()}

    @contextmanager
    def followed_by(self, t: TT, *, after: str):
        yield
        self.take(t, f"Expect '{OldParser.token_type_2_char[t]}' after {after}")

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


with_equal = {c + "=": TT(tt + 1) for c, tt in char_equal_tokens.items()}
extra_tokens = {"/": TT.SLASH}
all_tokens = char_tokens | char_equal_tokens | with_equal | keywords | extra_tokens


def fake_token(c: str | Parse):
    match c:
        case Parse("_str", _s, _e, s):
            return fake_token(typing.cast(str, s))
        case str():
            return Token(all_tokens[c], c, -99, None)  # TODO fix the -99 line numbers
        case _:
            raise ValueError(c)


class Parser:
    def __init__(self, source: str, report: Callable[[int, str, str], None]):
        self.lib = Lib()
        self.current = 0
        self.report = report
        self.source = source

    def parse_expr(self):
        got = self.lib.parse(self.source, ("rule", "expression"))
        logging.debug(got)
        shallower = de_tree(got)
        logging.info(shallower)
        return self.convert_expr(shallower)

    def convert_expr(self, tree: Parse | set) -> Expr:
        logging.debug("convert_expr( %s", tree)
        match tree:
            case Parse("assignment", _s, _e, (Parse("IDENTIFIER", __s, __e, ident), _eq, value)):
                return Assign(Token(TT.IDENTIFIER, ident, -99, None), self.convert_expr(value))
            case Parse("logic_and" | "logic_or", _s, _e, (left, ops)):
                expr = self.convert_expr(left)
                for op, right in ops:
                    expr = Logical(expr, fake_token(op), self.convert_expr(right))
                return expr
            case Parse("equality" | "comparison" | "term" | "factor", _s, _e, (left, ops)):
                expr = self.convert_expr(left)
                for op, right in ops:
                    expr = Binary(expr, fake_token(op), self.convert_expr(right))
                return expr

            case Parse("unary", _s, _e, (op, e)):
                return Unary(fake_token(op), self.convert_expr(e))

            case Parse("call", _s, _e, (callee, invokes)):
                e = self.convert_expr(callee)
                for _l, *args, _r in invokes:
                    match args:
                        case ():
                            exprs = []
                        case [[Parse("arguments", _s, _e, (arg0, args))]]:
                            without_comma = [arg0] + [arg for _comma, arg in args]
                            exprs = [self.convert_expr(e) for e in without_comma]
                            if len(exprs) > 255:
                                self.error(fake_token(args[254][0]), "Can't have more than 255 arguments.")
                        case [[arg0]]:
                            exprs = [self.convert_expr(arg0)]
                        case _:
                            raise RuntimeError("Impossible state")
                    e = Call(e, fake_token(")"), exprs)
                return e
            case Parse("arguments", _s, _e, _arg):
                raise RuntimeError("Impossible state:", tree)

            case Parse("primary", _s, _e, "true"):
                return Literal(True)
            case Parse("primary", _s, _e, "false"):
                return Literal(False)
            case Parse("primary", _s, _e, "nil"):
                return Literal(None)
            case Parse("primary", _s, _e, ("(", e, ")")):
                return Grouping(self.convert_expr(e))

            case Parse("NUMBER", _s, _e, e):
                if not isinstance(e, str):
                    raise ValueError(e)
                return Literal(float(e))
            case Parse("STRING", _s, _e, e):
                if not isinstance(e, str):
                    raise ValueError(e)
                return Literal(e.strip('"'))
            case Parse("IDENTIFIER", _s, _e, e):
                if not isinstance(e, str):
                    raise ValueError(e)
                return Variable(Token(TT.IDENTIFIER, e, -99, None))
            case Parse(rule, _s, _e, e):
                raise NotImplementedError(rule, e)
            case set():  # TODO actually used?
                possible = []
                for e in tree:
                    possible.append(self.convert_expr(e))
                if len(possible) == 1:
                    return possible[0]
                raise RuntimeError("Ambiguous conversion", tree, "->", *possible)
            case _:
                raise NotImplementedError(type(tree), tree)  # MAYBE convert these to Impossible State error

    def parse_stmt(self):
        got = self.lib.parse(self.source, ("rule", "program"))
        logging.debug(got)
        shallower = de_tree(got)
        logging.info(shallower)

        match shallower:
            case Parse("program", _s, _e, (*ops, _eof)):
                return [self.convert_stmt(e) for stmts in ops for e in stmts]
            case _:
                raise RuntimeError("Impossible State")

    def convert_stmt(self, tree: Parse) -> Stmt:
        logging.debug("convert_expr( %s", tree)
        match tree:
            case Parse(
                "funDecl",
                _s,
                _e,
                (
                    "fun",
                    Parse(
                        "function", __s, __e, (Parse("IDENTIFIER", _s1, _e1, ident), "(", *params, ")", body)
                    ),
                ),
            ):
                name = Token(TT.IDENTIFIER, ident, -99, None)
                match params:
                    case ():
                        names = []
                    case [[Parse("parameters", _s, _e, (arg0, args))]]:
                        without_comma = [arg0] + [arg for _comma, arg in args]
                        names = [Token(TT.IDENTIFIER, e.expr, -99, None) for e in without_comma]
                    case [[Parse("IDENTIFIER", _s, _e, arg0)]]:
                        names = [Token(TT.IDENTIFIER, arg0, -99, None)]
                    case _:
                        raise RuntimeError("Impossible state")
                match self.convert_stmt(body):
                    case Block(statements):
                        return Function(name, names, statements)
                    case _:
                        raise ValueError(body)
            case Parse("varDecl", _s, _e, ("var", Parse("IDENTIFIER", __s, __e, ident), *eq_value, ";")):
                name = Token(TT.IDENTIFIER, ident, -99, None)
                match eq_value:
                    case [(("=", e),)]:
                        return Var(name, self.convert_expr(e))
                    case []:
                        return Var(name, None)
                    case _:
                        raise RuntimeError("Impossible state")
            case Parse("exprStmt", _s, _e, (e, ";")):
                return Expression(self.convert_expr(e))
            case Parse("forStmt", _s, _e, ("for", "(", init, cond, ";", incr, ")", body)):
                raise NotImplementedError(init, "|||", cond, "|||", incr, "|||", body) # TODO implement
            case Parse("ifStmt", _s, _e, ("if", "(", cond, ")", true, *false)):
                return If(
                    self.convert_expr(cond),
                    self.convert_stmt(true),
                    self.convert_stmt(false[0][0][1]) if false else None,
                )
            case Parse("printStmt", _s, _e, ("print", e, ";")):
                return Print(self.convert_expr(e))
            case Parse("whileStmt", _s, _e, ("while", "(", cond, ")", statement)):
                return While(self.convert_expr(cond), self.convert_stmt(statement))
            case Parse("returnStmt", _s, _e, ("return", *expr, ";")):
                return Return(fake_token("return"), self.convert_expr(expr[0][0]) if expr else None)
            case Parse("block", _s, _e, ("{", *decl, "}")):
                return Block([self.convert_stmt(e) for e in decl[0]]) if decl else Block([])
            case Parse(rule, _s, _e, e):
                raise NotImplementedError(rule, e)
            case _:
                raise RuntimeError("Impossible state", type(tree), tree)

    def error(self, token: Token, message: str):
        """Optionally, for fatal errors raise the error"""
        lexeme = f"'{token.lexeme}'" if token.type != TT.EOF else "end"

        self.report(token.line, f" at {lexeme}", message)
        return ParseError()
