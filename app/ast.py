from typing import Tuple, override

from app.expression import Assign, Binary, Call, Expr, Grouping, Literal, Logical, Unary, Variable, Visitor
from app.scanner import Token, TokenType as TT
from app.statement import Block, Expression, Function, If, Print, Return, StmtVisitor, Var, While


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
    def visit_call(self, call: Call):
        return f"{self.print(call.callee)}({', '.join(self.print(a) for a in call.args)})"

    @override
    def visit_grouping(self, grouping: Grouping):
        return self.parens("group", grouping.value)

    @override
    def visit_logical(self, logical: Logical):
        """Uppercase is different than Binary"""
        return self.parens(logical.operator.lexeme.upper(), logical.left, logical.right)

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
    def visit_function(self, f: Function):
        body = self.visit_block(Block(f.body))
        params = ", ".join(p.lexeme for p in f.params)
        return f"fun {f.name.lexeme}({params}) {body}"

    @override
    def visit_if(self, i: If):
        els = f" else [{self.print(i.else_branch)}]" if i.else_branch else ""
        return f"if ({self.print(i.condition)}) [{self.print(i.then_branch)}]{els}"

    @override
    def visit_return(self, ret: Return):
        expr = f" {self.print(ret.value)}" if ret.value else ""
        return f"return{expr};"

    @override
    def visit_print(self, pr: Print):
        return f"print {self.print(pr.expr)};"

    def parens(self, name, *exprs: Tuple[Expr]):
        return f"({name} {' '.join(self.print(e) for e in exprs)})"

    @override
    def visit_var(self, var: Var):
        init = f" = {self.print(var.initializer)}" if var.initializer else ""
        return f"var {var.name.lexeme}{init};"

    @override
    def visit_while(self, w: While):
        return f"while ({self.print(w.condition)}) [{self.print(w.body)}]"


if __name__ == "__main__":
    expr = Binary(
        Unary(Token(TT.MINUS, "-", 1, None), Literal(123)),
        Token(TT.STAR, "*", 1, None),
        Grouping(Literal(45.67)),
    )

    print(AstPrinter().print(Print(expr)))

    print(
        AstPrinter().print(
            Call(
                Variable(Token(TT.IDENTIFIER, "a", 0, None)), Token(TT.RIGHT_PAREN, ")", 0, 0), [Literal(123)]
            )
        )
    )

    def type_test() -> Visitor[str]:
        return AstPrinter()

    visitor = type_test()
    print(v := visitor.visit_binary(expr))
