from enum import Enum, auto
from typing import Self, cast, override

from app.expression import Assign, Expr, Variable
from app.interpreter import Interpreter
from app.runtime import CompileErrCB
from app.scanner import Token
from app.statement import BaseVisitor, Block, Class, Function, Return, Stmt, Var


class VarState(Enum):
    NONE = auto()
    INITIALIZING = auto()
    SET = auto()


class Resolver(BaseVisitor):
    def __init__(
        self,
        interpreter: Interpreter,
        on_error: CompileErrCB,
        parent: Self | None = None,
    ):
        self.interpreter = interpreter
        self.scope: dict[str, VarState] = {}  # Ignored if parent is None (global scope)
        self.parent = parent
        self.on_error = on_error

    @override
    def visit_block(self, block: Block) -> None:
        new_scope = Resolver(self.interpreter, self.on_error, self)
        new_scope.accept_any(block.statements)

    @override
    def visit_var(self, var: Var):
        self.declare(var.name, VarState.INITIALIZING)
        if var.initializer:
            self.accept_any(var.initializer)
        self.scope[var.name.lexeme] = VarState.SET

    @override
    def visit_variable(self, variable: Variable):
        if self.parent and self.scope.get(variable.name.lexeme) == VarState.INITIALIZING:
            self.on_error(variable.name, "Can't read local variable in its own initializer.")
        self.resolve_local(variable, variable.name.lexeme)

    @override
    def visit_assign(self, assign: Assign):
        self.accept_any(assign.value)
        self.resolve_local(assign, assign.name.lexeme)

    @override
    def visit_function(self, f: Function) -> None:
        self.declare(f.name, VarState.SET)

        new_scope = Resolver(self.interpreter, self.on_error, self)
        for p in f.params:
            new_scope.declare(p, VarState.SET)

        new_scope.accept_any(f.body)

    @override
    def visit_class(self, c: Class):
        self.declare(c.name, VarState.SET)
        for m in c.methods:
            m.accept(self)

    def declare(self, t: Token, state: VarState):
        if self.parent and t.lexeme in self.scope:
            self.on_error(t, "Already a variable with this name in this scope.")
        self.scope[t.lexeme] = state

    def resolve_local(self, e: Expr, name: str, n=0):
        if not self.parent:
            return
        if name in self.scope:
            self.interpreter.resolve(e, n)
        else:
            self.parent.resolve_local(e, name, n + 1)


class ReturnInFunc(BaseVisitor):
    """Book says it's better to do one pass of the tree doing multiple checks. But this is much easier to read."""
    def __init__(self, on_error: CompileErrCB):
        self.on_error = on_error

    def visit_return(self, ret: Return):
        self.on_error(ret.keyword, "Can't return from top-level code.")

    def visit_function(self, f: Function):
        pass  # Stop recursing


def static_analysis(interpreter: Interpreter, e: Expr | list[Stmt], on_error: CompileErrCB):
    """Perform static analysis on the given statements."""
    Resolver(interpreter, on_error=on_error).accept_any(e)
    ReturnInFunc(on_error=on_error or interpreter.runtime_error).accept_any(e)
