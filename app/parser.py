from typing import Callable

from app.expression import Assign, Binary, Call, Grouping, Literal, Logical, Unary, Variable
from app.scanner import Token, TokenType as TT
from app.statement import Block, Expression, Function, If, Print, Return, Var, While


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

    def declaration(self):
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
        name = self.take(f"Expect {kind} name.", TT.IDENTIFIER)
        self.take(f"Expect '(' after {kind} name.", TT.LEFT_PAREN)
        
        params = []
        if not self.try_take(TT.RIGHT_PAREN):
            params.append(self.take("Expect parameter name.", TT.IDENTIFIER))
            while self.try_take(TT.COMMA):
                params.append(self.take("Expect parameter name.", TT.IDENTIFIER))
            self.take("Expect ')' after parameters.", TT.RIGHT_PAREN)

        self.take(f"Expect '{{' before {kind} body.", TT.LEFT_BRACE)
        return Function(name, params, self.block())

    def var_declaration(self):
        name = self.take("Expect variable name.", TT.IDENTIFIER)
        initializer = None
        if self.try_take(TT.EQUAL):
            initializer = self.expression()
        self.take("Expect ';' after variable declaration.", TT.SEMICOLON)
        return Var(name, initializer)

    def statement(self):
        if self.try_take(TT.FOR):
            return self.for_statement()

        if self.try_take(TT.PRINT):
            st = Print(self.expression())
            self.take("Expect ';' after value.", TT.SEMICOLON)
            return st

        if self.try_take(TT.IF):
            self.take("Expect '(' after 'if'.", TT.LEFT_PAREN)
            condition = self.expression()
            self.take("Expect ')' after condition.", TT.RIGHT_PAREN)
            then_branch = self.statement()
            else_branch = None
            if self.try_take(TT.ELSE):
                else_branch = self.statement()
            return If(condition, then_branch, else_branch)

        if ret := self.try_take(TT.RETURN):
            if self.try_take(TT.SEMICOLON):
                return Return(ret, None)
            
            st = Return(ret, self.expression())
            self.take("Expect ';' after return value.", TT.SEMICOLON)
            return st  # MAYBE refactor this to a small context manager
        
        if self.try_take(TT.WHILE):
            self.take("Expect '(' after 'while'.", TT.LEFT_PAREN)
            condition = self.expression()
            self.take("Expect ')' after condition.", TT.RIGHT_PAREN)
            body = self.statement()
            return While(condition, body)

        if self.try_take(TT.LEFT_BRACE):
            return Block(self.block())
        return self.expression_statement()

    def expression_statement(self):
        st = Expression(self.expression())
        self.take("Expect ';' after expression.", TT.SEMICOLON)
        return st
    
    def for_statement(self):
        self.take("Expect '(' after 'for'.", TT.LEFT_PAREN)

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
            self.take("Expect ';' after loop condition.", TT.SEMICOLON)
        
        if self.try_take(TT.RIGHT_PAREN):
            increment = None
        else:
            increment = self.expression()
            self.take("Expect ')' after for clauses.", TT.RIGHT_PAREN)

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
                break

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

    def expression(self):
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
        p = self.take("Expect ')' after arguments.", TT.RIGHT_PAREN)
        return Call(callee, p, args)


    def take_binary(self, f, *types, tt=Binary):
        e = f()
        while op := self.try_take(*types):
            e = tt(e, op, f())
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
