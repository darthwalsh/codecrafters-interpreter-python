from typing import override

from app.expression import Assign, Expr, Variable
from app.interpreter import Interpreter
from app.statement import BaseVisitor, Block, Function, Stmt, Var


class Resolver(BaseVisitor):
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter

    @override
    def visit_block(self, block: Block) -> None:
        raise NotImplementedError

    @override
    def visit_var(self, var: Var):
        raise NotImplementedError

    @override
    def visit_variable(self, variable: Variable):
        raise NotImplementedError

    @override
    def visit_assign(self, assign: Assign):
        raise NotImplementedError

    @override
    def visit_function(self, f: Function) -> None:
        raise NotImplementedError

    def resolve(self, e: Expr | Stmt):
        e.accept(self)
