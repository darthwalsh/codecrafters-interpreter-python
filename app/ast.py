from app.expression import Binary, Expr, Grouping, Literal, Unary, Variable, Visitor


from typing import Tuple, override

from app.statement import Expression, Print, StmtVisitor, Var


class AstPrinter(Visitor[str], StmtVisitor[str]):
    def print(self, expr: Expr | list[str]):
        if isinstance(expr, list):
            return " ".join(self.print(e) for e in expr)
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
    
    @override
    def visit_variable(self, variable: Variable):
        return variable.name.lexeme
    
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
