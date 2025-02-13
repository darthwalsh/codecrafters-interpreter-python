from app.expression import Binary, Expr, Grouping, Literal, Unary, Visitor


from typing import Tuple, override


class AstPrinter(Visitor[str]):
    def print(self, expr: Expr):
        return expr.accept(self)

    @override
    def visit_binary(self, binary: Binary):
        return self.parens(binary.operator.lexeme, binary.left, binary.right)

    @override
    def visit_grouping(self, grouping: Grouping):
        return self.parens("group", grouping.value)

    @override
    def visit_literal(self, literal: Literal):
        match v := literal.value:
            case bool():
                return str(v).lower()
            case None:
                return "nil"
            case _:
                return str(v)

    @override
    def visit_unary(self, unary: Unary):
        return self.parens(unary.operator.lexeme, unary.right)

    def parens(self, name, *exprs: Tuple[Expr]):
        return f"({name} {' '.join(e.accept(self) for e in exprs)})"
