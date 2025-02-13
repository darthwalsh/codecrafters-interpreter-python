import math
from typing import IO, override
from app.expression import Expr, Binary, Grouping, Literal, Unary, Visitor
from app.scanner import TokenType as TT


class Interpreter(Visitor[object]):
    def interpret(self, expr: Expr, file: IO):
        o = self.evaluate(expr)
        print(self.stringify(o), file=file)

    def stringify(self, o):
        match o:
            case None:
                return "nil"
            case bool():
                return str(o).lower()
            case float() if o.is_integer():
                return str(int(o))
            case _:
                return str(o)

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
            case TT.PLUS:
                return left + right
            case TT.SLASH:
                try:
                    return left / right
                except ZeroDivisionError:
                    if not left: # 0/0
                        return math.nan
                    return left * math.inf
            case TT.STAR:
                return left * right

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
                return -right
            case TT.BANG:
                return not self.truthy(right)
            case _:
                raise RuntimeError("Impossible state")

    def truthy(self, o: object):
        """Ruby semantics"""
        return o not in (False, None)
