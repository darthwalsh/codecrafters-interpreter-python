import math
from typing import IO, Callable, override
from app.expression import Expr, Binary, Grouping, Literal, Unary, Visitor
from app.scanner import Token, TokenType as TT


def stringify(o):
    match o:
        case None:
            return "nil"
        case bool():
            return str(o).lower()
        case float() if o.is_integer():
            return str(int(o))
        case _:
            return str(o)


def truthy(o: object):
    """Ruby semantics"""
    return o not in (False, None)


class LoxRuntimeError(Exception):
    """Don't shadow builtin RuntimeError"""

    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token
        self.message = message


class Interpreter(Visitor[object]):
    def __init__(self, err: Callable):
        self.err = err

    def interpret(self, expr: Expr, file: IO):
        try:
            o = self.evaluate(expr)
            print(stringify(o), file=file)
        except LoxRuntimeError as e:
            self.err(e)

    def evaluate(self, expr: Expr):
        return expr.accept(self)

    @override
    def visit_binary(self, binary: Binary):
        left, right = self.evaluate(binary.left), self.evaluate(binary.right)
        match binary.operator.type:
            case TT.BANG_EQUAL:
                return left != right
            case TT.EQUAL_EQUAL:
                return left == right

            case TT.PLUS:
                if isinstance(left, (str, float)) and type(left) is type(right):
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
    def visit_grouping(self, grouping: Grouping):
        return self.evaluate(grouping.value)

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
