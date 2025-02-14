from typing import Tuple, override

from app.expression import Assign, Binary, Expr, Grouping, Literal, Unary, Variable, Visitor
from app.scanner import Token, TokenType as TT
from app.statement import Block, Expression, Print, StmtVisitor, Var


class AstPrinter(Visitor[str], StmtVisitor[str]):
    def print(self, expr: Expr | list[str]):
        if isinstance(expr, list):
            return " ".join(self.print(e) for e in expr)
        return expr.accept(self)

    @override
    def visit_assign(self, assign: Assign):
        return self.parens(f"= {assign.name.lexeme}", assign.value)

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

    @override
    def visit_variable(self, variable: Variable):
        return variable.name.lexeme
    
    @override
    def visit_block(self, block: Block):
        return f"{{ {' '.join(self.print(s) for s in block.statements)} }}"

    @override
    def visit_expression(self, ex: Expression):
        return f"{self.print(ex.expr)};"

    @override
    def visit_print(self, pr: Print):
        return f"print {self.print(pr.expr)};"

    def parens(self, name, *exprs: Tuple[Expr]):
        return f"({name} {' '.join(self.print(e) for e in exprs)})"

    @override
    def visit_var(self, var: Var):
        init = f" = {self.print(var.initializer)}" if var.initializer else ""
        return f"var {var.name.lexeme}{init};"


if __name__ == "__main__":
    expr = Binary(
        Unary(Token(TT.MINUS, "-", 1, None), Literal(123)),
        Token(TT.STAR, "*", 1, None),
        Grouping(Literal(45.67)),
    )

    print(AstPrinter().print(Print(expr)))

    def type_test() -> Visitor[str]:
        return AstPrinter()

    visitor = type_test()
    print(v := visitor.visit_binary(expr))
