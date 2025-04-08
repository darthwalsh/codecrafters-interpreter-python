from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from app.environment import Environment
from app.runtime import ReturnUnwind
from app.statement import Function

if TYPE_CHECKING:  # pragma: no cover
    from app.classes import LoxInstance
    from app.interpreter import Interpreter

class LoxCallable(ABC):
    @abstractmethod
    def __call__(self, intr: "Interpreter", args: list[object]) -> object: ...

    @property
    @abstractmethod
    def arity(self) -> int: ...


@dataclass
class LoxFunction(LoxCallable):
    decl: Function
    closure: Environment

    @property
    @override
    def arity(self):
        return len(self.decl.params)

    @override
    def __call__(self, intr: "Interpreter", args: list[object]):
        env = Environment(self.closure)
        for a, p in zip(args, self.decl.params, strict=True):
            env[p.lexeme] = a

        try:
            intr.execute_block(self.decl.body, env)
        except ReturnUnwind as e:
            return e.value
        
    def bind(self, instance: "LoxInstance"):
        """Bind a method to an instance"""
        env = Environment(self.closure)
        env["this"] = instance
        return self.__class__(self.decl, env)  # Create instance of subclass type

    def __str__(self):
        return f"<fn {self.decl.name.lexeme}>"


@dataclass
class NativeFunction(LoxCallable):
    """Allows function that take no arguments"""
    func: Callable[[], object]

    @property
    @override
    def arity(self):
        # Would use len(inspect.signature(self.func).parameters) but that doesn't work on built-in functions
        return 0

    @override
    def __call__(self, _intr, _args):
        return self.func()

    def __str__(self):
        # Would be more fun to also print native function __name__ but oh well...
        return "<native fn>"
