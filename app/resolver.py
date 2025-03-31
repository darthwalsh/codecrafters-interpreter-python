from enum import Enum, auto
from typing import Self, override

from app.expression import Assign, Expr, Variable
from app.interpreter import Interpreter
from app.runtime import LoxRuntimeError
from app.statement import BaseVisitor, Block, Function, Stmt, Var


class VarState(Enum):
    NONE = auto()
    INITIALIZING = auto()
    SET = auto()


class Resolver(BaseVisitor):
    def __init__(self, interpreter: Interpreter, parent: Self | None = None):
        self.interpreter = interpreter
        self.scope: dict[str, VarState] = {}  # Ignored if parent is None (global scope)
        self.parent = parent

    @override
    def visit_block(self, block: Block) -> None:
        new_scope = Resolver(self.interpreter, self)
        new_scope.resolve(block.statements)

    @override
    def visit_var(self, var: Var):
        self.scope[var.name.lexeme] = VarState.INITIALIZING
        if var.initializer:
            self.resolve(var.initializer)
        self.scope[var.name.lexeme] = VarState.SET

    @override
    def visit_variable(self, variable: Variable):
        if self.parent and self.scope.get(variable.name.lexeme) == VarState.INITIALIZING:
            ex = LoxRuntimeError(variable.name, "Can't read local variable in its own initializer.")
            self.interpreter.runtime_error(ex)
        self.resolve_local(variable, variable.name.lexeme)

    @override
    def visit_assign(self, assign: Assign):
        self.resolve(assign.value)
        self.resolve_local(assign, assign.name.lexeme)

    @override
    def visit_function(self, f: Function) -> None:
        self.scope[f.name.lexeme] = VarState.SET

        new_scope = Resolver(self.interpreter, self)
        new_scope.scope = {p.lexeme: VarState.SET for p in f.params}

        new_scope.resolve(f.body)

    def resolve(self, e: Expr | list[Stmt]):
        if isinstance(e, Expr):
            e.accept(self)
            return
        for stmt in e:
            stmt.accept(self)

    def resolve_local(self, e: Expr, name: str, n=0):
        if not self.parent:
            return
        if name in self.scope:
            self.interpreter.resolve(e, n)
        else:
            self.parent.resolve_local(e, name, n + 1)


# TODO https://craftinginterpreters.com/resolving-and-binding.html#resolution-errors
