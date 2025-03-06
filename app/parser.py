import sys
from collections.abc import Callable
from contextlib import contextmanager
import typing

from app.bnf_lib import Lib, Parse
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


class NotConvertible(Exception):
    pass


with_equal = {c + "=": TT(tt + 1) for c, tt in char_equal_tokens.items()}
extra_tokens = {"/": TT.SLASH}
all_tokens = char_tokens | char_equal_tokens | with_equal | keywords | extra_tokens


def fake_token(c: str | Parse):
    match c:
        case Parse("_str", _s, _e, s):
            return fake_token(typing.cast(str, s))
        case str():
            return Token(all_tokens[c], c, -99, None)
        case _:
            raise ValueError(c)


def convert_stmt(tree) -> Stmt:
    raise NotImplementedError


def convert_expr(tree) -> Expr:
    print("convert_expr(", tree, file=sys.stderr, flush=True)  # TODONT
    match tree:
        case Parse("logic_and" | "logic_or", _s, _e, (left, ops)):
            expr = convert_expr(left)
            if not isinstance(ops[1], tuple):
                # HACK should be Tuple[Tuple[str, Expr], ...], unless there is only one then got untupled to Tuple[str, Expr]? maybe remove this hack
                ops = (ops,)
            for op, right in ops:
                expr = Logical(expr, fake_token(op), convert_expr(right))
            return expr
        case Parse("equality" | "comparison" | "term" | "factor", _s, _e, Parse("_concat", __s, __e, (left, ops))):
            expr = convert_expr(left)
            if not isinstance(ops[1], tuple):  # HACK ditto
                ops = (ops,)
            for op, right in ops:
                expr = Binary(expr, fake_token(op), convert_expr(right))
            return expr

        case Parse("unary", _s, _e, Parse("_concat", __s, __e, (op, e))):
            return Unary(fake_token(op), convert_expr(e))

        case Parse("call", _s, _e, (callee, *invokes)):
            raise NotImplementedError(
                "TODO the parse tree is wrong -- should NOT be flattening this part of the tree "
            )
            e = convert_expr(callee)
            for _l, *args, _r in invokes:
                e = Call(e, fake_token(")"), [convert_expr(a) for a in args])
            return e

        case Parse("primary", _s, _e, "true"):
            return Literal(True)
        case Parse("primary", _s, _e, "false"):
            return Literal(False)
        case Parse("primary", _s, _e, "Nil"):
            return Literal(None)
        case Parse("primary", _s, _e, Parse("_concat", _s4, _e4, (Parse("_str", __s, __e, "("), e, Parse("_str", _s_, _e_, ")")))):
            return Grouping(convert_expr(e))

        case Parse("NUMBER", _s, _e, e):
            if not isinstance(e, str):
                raise ValueError(e)
            return Literal(float(e))
        case Parse("STRING", _s, _e, e):
            if not isinstance(e, str):
                raise ValueError(e)
            return Literal(e.strip('"'))
        case Parse("IDENTIFIER", _s, _e, e):
            if e in keywords:
                raise NotConvertible("KeywordError")  # TODO too late for this. `true` will parse as primary(_true) || primary(_str(true))) -- maybe use the sorted production rules, and in a tie for frozen-set, only take the first?
            if not isinstance(e, str):
                raise ValueError(e)
            return Variable(Token(TT.IDENTIFIER, e, -99, None))
        
        case Parse(rule, _s, _e, (e,)):
            print("Drilling through trivial tuple:", rule, file=sys.stderr, flush=True)
            return convert_expr(e)
        case Parse(rule, _s, _e, Parse()):
            print("Drilling through trivial parse node:", rule, file=sys.stderr, flush=True)  # TODO too powerful, shouldn't drill through if...? Causes worse error messages later on
            return convert_expr(tree.expr)
        case Parse(rule, _s, _e, e):
            raise NotImplementedError(rule, e)
        case set():
            possible = []
            for e in tree:
                try:
                    possible.append(convert_expr(e))
                except NotConvertible:
                    pass
            if len(possible) == 1:
                return possible[0]
            raise RuntimeError("Ambiguous conversion", tree, "->", *possible)
        case _:
            raise NotImplementedError(type(tree), tree)


class Parser:
    def __init__(self, source: str, report: Callable[[int, str, str], None]):
        self.lib = Lib()
        self.current = 0
        self.report = report
        self.source = source

    def parse_expr(self):
        got = self.lib.parse(self.source, ("rule", "expression"))
        print(got)
        return convert_expr(got)

    def parse_stmt(self):
        got = self.lib.parse(self.source, ("rule", "program"))
        print(got)
        return convert_stmt(got)
