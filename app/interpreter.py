import math
import sys
from collections.abc import MutableMapping
from time import time
from typing import override

from app import func
from app.environment import Environment
from app.expression import (
    Assign,
    Binary,
    Call,
    Expr,
    Get,
    Grouping,
    Literal,
    Logical,
    Set,
    This,
    Unary,
    Variable,
    Visitor,
)
from app.runtime import LoxRuntimeError, ReturnUnwind, RuntimeErrCB
from app.scanner import Token
from app.scanner import TokenType as TT
from app.statement import Block, Class, Expression, Function, If, Print, Return, Stmt, StmtVisitor, Var, While


def stringify(o):
    match o:
        case None:
            return "nil"
        case bool():
            return str(o).lower()
        case 0.0 if math.copysign(1, o) == -1:
            return "-0"
        case float() if o.is_integer():
            return str(int(o))
        case func if callable(o) and not isinstance(o, LoxClass):
            # Would be more fun to also print native function __name__ but whatever...
            return f"<fn {func.__name__}>" if func not in default_global.values() else "<native fn>"
        case _:
            return str(o)


def is_equal(x: object, y: object):
    return type(x) is type(y) and x == y


def truthy(o: object):
    """Ruby semantics"""
    return o is not False and o is not None


def clock():
    return time()


default_global = dict(clock=clock)


class Interpreter(Visitor[object], StmtVisitor[None]):
    def __init__(self, runtime_error: RuntimeErrCB, file=sys.stdout):
        self.global_env = Environment()
        self.environment = self.global_env
        self.locals = RefEqualityDict[Expr, int]()

        for name, val in default_global.items():
            self.global_env[name] = val

        self.runtime_error = runtime_error
        self.file = file  # MAYBE instead of taking in the IO object, it should take a regular callback?

    def interpret(self, e: Expr | list[Stmt]):
        try:
            if isinstance(e, list):
                for st in e:
                    self.execute(st)
            else:
                o = self.evaluate(e)
                print(stringify(o), file=self.file)
        except LoxRuntimeError as ex:
            self.runtime_error(ex)

    def execute(self, st: Stmt):
        st.accept(self)

    def evaluate(self, expr: Expr):
        return expr.accept(self)

    @override
    def visit_assign(self, assign: Assign):
        self.resolved_env(assign).assign(assign.name, o := self.evaluate(assign.value))
        return o

    @override
    def visit_binary(self, binary: Binary):
        left, right = self.evaluate(binary.left), self.evaluate(binary.right)
        match binary.operator.type:
            case TT.BANG_EQUAL:
                return not is_equal(left, right)
            case TT.EQUAL_EQUAL:
                return is_equal(left, right)

            case TT.PLUS:
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                if isinstance(left, float) and isinstance(right, float):
                    return left + right
                raise LoxRuntimeError(binary.operator, "Operands must be two numbers or two strings.")
            case _:
                pass

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
        callee_arity = func.arity(callee)
        if len(args) != callee_arity:
            raise LoxRuntimeError(call.paren, f"Expected {callee_arity} arguments but got {len(args)}.")

        return callee(*args)

    @override
    def visit_get(self, get: Get):
        obj = self.evaluate(get.object)
        if not isinstance(obj, LoxInstance):
            raise LoxRuntimeError(get.name, "Only instances have properties.")
        return obj[get.name]

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
    def visit_set(self, set: Set):
        obj = self.evaluate(set.object)
        if not isinstance(obj, LoxInstance):
            raise LoxRuntimeError(set.name, "Only instances have fields.")
        obj[set.name] = self.evaluate(set.value)

    @override
    def visit_this(self, this: This):
        raise NotImplementedError

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
        return self.resolved_env(variable)[variable.name]

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
    def visit_class(self, c: Class):
        clss = LoxClass(c.name.lexeme)
        for m in c.methods:
            if m.name.lexeme == "init":
                raise NotImplementedError
            setattr(clss, m.name.lexeme, self.make_function(m))
        self.environment[c.name.lexeme] = clss

    @override
    def visit_expression(self, ex: Expression):
        self.evaluate(ex.expr)

    @override
    def visit_function(self, f: Function):
        self.environment[f.name.lexeme] =  self.make_function(f)

    def make_function(self, f: Function):
        closure = self.environment

        def fun(*args: object) -> object:
            env = Environment(closure)
            for a, p in zip(args, f.params):
                env[p.lexeme] = a

            try:
                self.execute_block(f.body, env)
            except ReturnUnwind as ret:
                return ret.value

        func.shim(fun, f.name.lexeme, [p.lexeme for p in f.params])
        return fun

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

    def resolved_env(self, e: Expr):
        distance = self.locals.get(e)
        if distance is not None:
            return self.environment.ancestor(distance)
        return self.global_env

    def resolve(self, e: Expr, n: int):
        self.locals[e] = n


class RefEqualityDict[K, V](MutableMapping[K, V]):
    def __init__(self):
        self.vals: dict[int, V] = {}

    def __delitem__(self, key: K):
        del self.vals[id(key)]

    def __getitem__(self, key: K):
        return self.vals[id(key)]

    def __setitem__(self, key: K, value: V):
        self.vals[id(key)] = value

    def __iter__(self):  # pragma: no cover
        raise RuntimeError  # Not have the keys, only the values

    def __len__(self):
        return len(self.vals)


class LoxClass:  # TODO: make a python class?
    def __init__(self, name: str):
        self.name = name

    def __call__(self) -> object:  # TODO *args: object
        instance = LoxInstance(self)
        if hasattr(self, "init"):
            raise NotImplementedError
        return instance

    def __str__(self):
        return self.name


class LoxInstance:
    def __init__(self, c: LoxClass):
        self.c = c
        self.fields: dict[str, object] = {}

    def __getitem__(self, name: Token):
        try:
            return self.fields[name.lexeme]
        except KeyError:
            if hasattr(self.c, name.lexeme):
                return getattr(self.c, name.lexeme)
            raise LoxRuntimeError(name, f"Undefined property '{name.lexeme}'.")

    def __setitem__(self, name: Token, value: object):
        self.fields[name.lexeme] = value

    def __str__(self):
        return f"{self.c.name} instance"
