import math
import sys
from collections.abc import Callable
from time import time
from typing import override

from app.environment import Environment
from app.expression import Assign, Binary, Call, Expr, Grouping, Literal, Logical, Unary, Variable, Visitor
from app.func import LoxFunction
from app.runtime import LoxRuntimeError, ReturnUnwind
from app.scanner import TokenType as TT
from app.statement import Block, Expression, Function, If, Print, Return, Stmt, StmtVisitor, Var, While


def stringify(o):
    match o:
        case None:
            return "nil"
        case bool():
            return str(o).lower()
        case float() if o.is_integer():
            return str(int(o))
        case func if callable(o):
            return f"<fn {func.__name__}>"
        case _:
            return str(o)


def truthy(o: object):
    """Ruby semantics"""
    return o not in (False, None)


class Interpreter(Visitor[object], StmtVisitor[None]):
    def __init__(self, runtime_error: Callable, file=sys.stdout):
        self.global_env = Environment()
        self.environment = self.global_env

        def clock(_intr: Interpreter, _args: list[object]):
            return time()

        clock.arity = 0  # MAYBE use LoxCallable ABC from LoxFunction?
        self.global_env["clock"] = clock

        self.runtime_error = runtime_error
        self.file = file  # Maybe instead of taking in the IO object, it should take a regular callback?

    def interpret(self, e: Expr | list[Stmt]):
        try:
            try:
                if isinstance(e, list):
                    for st in e:
                        self.execute(st)
                else:
                    o = self.evaluate(e)
                    print(stringify(o), file=self.file)
            except ReturnUnwind as e:
                # TODO in chapter 11 change this from runtime to compile error
                raise LoxRuntimeError(
                    e.token, f"Tried to return '{stringify(e.value)}' outside function."
                ) from e
        except LoxRuntimeError as e:
            self.runtime_error(e)

    def execute(self, st: Stmt):
        st.accept(self)

    def evaluate(self, expr: Expr):
        return expr.accept(self)

    @override
    def visit_assign(self, assign: Assign):
        self.environment.assign(assign.name, o := self.evaluate(assign.value))
        return o

    @override
    def visit_binary(self, binary: Binary):
        left, right = self.evaluate(binary.left), self.evaluate(binary.right)
        match binary.operator.type:
            case TT.BANG_EQUAL:
                return left != right
            case TT.EQUAL_EQUAL:
                return left == right

            case TT.PLUS:
                if isinstance(left, str | float) and type(left) is type(right):
                    return left + right
                raise LoxRuntimeError(binary.operator, "Operands must be two numbers or two strings.")

        if not isinstance(left, float) or not isinstance(right, float):
            raise LoxRuntimeError(binary.operator, "Operands must be numbers.")
        match binary.operator.type:
            case TT.GREATER:
                return left > right
            case TT.GREATER_EQUAL:
                return left >= right
            case TT.LESS:
                return left < right
            case TT.LESS_EQUAL:
                return left <= right

            case TT.MINUS:
                return left - right
            case TT.STAR:
                return left * right

            case TT.SLASH:
                try:
                    return left / right
                except ZeroDivisionError:
                    if not left:  # 0/0
                        return math.nan
                    return left * math.inf
            case _:
                raise RuntimeError("Impossible state")

    @override
    def visit_call(self, call: Call):
        callee = self.evaluate(call.callee)
        args = [self.evaluate(a) for a in call.args]

        if not callable(callee):
            raise LoxRuntimeError(call.paren, "Can only call functions and classes.")
        if len(args) != callee.arity:
            raise LoxRuntimeError(call.paren, f"Expected {callee.arity} arguments but got {len(args)}.")

        return callee(self, args)

    @override
    def visit_grouping(self, grouping: Grouping):
        return self.evaluate(grouping.value)

    @override
    def visit_logical(self, logical: Logical):
        left = self.evaluate(logical.left)
        match logical.operator.type:
            case TT.OR:
                if truthy(left):
                    return left
            case TT.AND:
                if not truthy(left):
                    return left
            case _:
                raise RuntimeError("Impossible state")
        return self.evaluate(logical.right)

    @override
    def visit_literal(self, literal: Literal):
        return literal.value

    @override
    def visit_unary(self, unary: Unary):
        right = self.evaluate(unary.right)
        match unary.operator.type:
            case TT.MINUS:
                if isinstance(right, float):
                    return -right
                raise LoxRuntimeError(unary.operator, "Operand must be a number.")
            case TT.BANG:
                return not truthy(right)
            case _:
                raise RuntimeError("Impossible state")

    @override
    def visit_variable(self, variable: Variable):
        return self.environment[variable.name]

    @override
    def visit_block(self, block: Block):
        self.execute_block(block.statements, Environment(self.environment))

    def execute_block(self, statements: list[Stmt], env: Environment):
        orig, self.environment = self.environment, env
        try:
            for st in statements:
                self.execute(st)
        finally:
            self.environment = orig

    @override
    def visit_expression(self, ex: Expression):
        self.evaluate(ex.expr)

    @override
    def visit_function(self, f: Function):
        self.environment[f.name.lexeme] = LoxFunction(f, self.environment)

    @override
    def visit_if(self, i: If):
        if truthy(self.evaluate(i.condition)):
            self.execute(i.then_branch)
        elif i.else_branch:
            self.execute(i.else_branch)

    @override
    def visit_return(self, ret: Return):
        """Agree with the book logic, would be a pain to check each recursive call here for pending return!"""
        o = self.evaluate(ret.value) if ret.value else None
        raise ReturnUnwind(o, ret.keyword)

    @override
    def visit_print(self, pr: Print):
        print(stringify(self.evaluate(pr.expr)), file=self.file)

    @override
    def visit_var(self, var: Var):
        self.environment[var.name.lexeme] = self.evaluate(var.initializer) if var.initializer else None

    @override
    def visit_while(self, w: While):
        while truthy(self.evaluate(w.condition)):
            self.execute(w.body)
