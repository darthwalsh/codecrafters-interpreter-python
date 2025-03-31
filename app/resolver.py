from collections.abc import Callable
from enum import Enum, auto
from typing import Self, override

from app.expression import Assign, Expr, Variable
from app.interpreter import Interpreter
from app.runtime import LoxRuntimeError
from app.statement import BaseVisitor, Block, Function, Return, Stmt, Var


class VarState(Enum):
    NONE = auto()
    INITIALIZING = auto()
    SET = auto()


class Resolver(BaseVisitor):
    def __init__(
        self,
        interpreter: Interpreter,
        parent: Self | None = None,
        on_error: Callable[[LoxRuntimeError], None] | None = None,
    ):
        self.interpreter = interpreter
        self.scope: dict[str, VarState] = {}  # Ignored if parent is None (global scope)
        self.parent = parent
        self.on_error = on_error if on_error else parent.on_error if parent else interpreter.runtime_error

    @override
    def visit_block(self, block: Block) -> None:
        new_scope = Resolver(self.interpreter, self)
        new_scope.accept_any(block.statements)

    @override
    def visit_var(self, var: Var):
        if var.name.lexeme in self.scope:
            ex = LoxRuntimeError(var.name, "Already a variable with this name in this scope.")
            self.on_error(ex)
        self.scope[var.name.lexeme] = VarState.INITIALIZING
        if var.initializer:
            self.accept_any(var.initializer)
        self.scope[var.name.lexeme] = VarState.SET

    @override
    def visit_variable(self, variable: Variable):
        if self.parent and self.scope.get(variable.name.lexeme) == VarState.INITIALIZING:
            ex = LoxRuntimeError(variable.name, "Can't read local variable in its own initializer.")
            self.on_error(ex)
        self.resolve_local(variable, variable.name.lexeme)

    @override
    def visit_assign(self, assign: Assign):
        self.accept_any(assign.value)
        self.resolve_local(assign, assign.name.lexeme)

    @override
    def visit_function(self, f: Function) -> None:
        self.scope[f.name.lexeme] = VarState.SET

        new_scope = Resolver(self.interpreter, self)
        new_scope.scope = {p.lexeme: VarState.SET for p in f.params}

        new_scope.accept_any(f.body)

    def resolve_local(self, e: Expr, name: str, n=0):
        if not self.parent:
            return
        if name in self.scope:
            self.interpreter.resolve(e, n)
        else:
            self.parent.resolve_local(e, name, n + 1)


class ReturnInFunc(BaseVisitor):
    def __init__(self, on_error: Callable[[LoxRuntimeError], None]):
        self.on_error = on_error

    def visit_return(self, ret: Return):
        self.on_error(LoxRuntimeError(ret.keyword, "Can't return from top-level code."))

    def visit_function(self, f: Function):
        pass  # Stop recursing


def static_analysis(
    interpreter: Interpreter, e: Expr | list[Stmt], on_error: Callable[[LoxRuntimeError], None] | None = None
):
    """Perform static analysis on the given statements."""
    Resolver(interpreter, on_error=on_error).accept_any(e)
    ReturnInFunc(on_error=on_error or interpreter.runtime_error).accept_any(e)
