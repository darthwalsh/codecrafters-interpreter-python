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
        raise NotImplementedError
        # return self.parens(binary.operator.lexeme, binary.left, binary.right)

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
        return o not in (False, None)
