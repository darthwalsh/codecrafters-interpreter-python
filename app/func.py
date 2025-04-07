import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from app.environment import Environment
from app.runtime import ReturnUnwind
from app.statement import Function


class LoxCallable(ABC):
    @abstractmethod
    def __call__(self, intr, args: list[object]) -> object: ...

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
    def __call__(self, intr, args: list[object]):
        # MAYBE figure out circular type hint on intr: Interpreter i.e. https://stackoverflow.com/a/69049426/771768
        env = Environment(self.closure)
        for a, p in zip(args, self.decl.params, strict=True):
            env[p.lexeme] = a

        try:
            intr.execute_block(self.decl.body, env)
        except ReturnUnwind as e:
            return e.value

    def __str__(self):
        return f"<fn {self.decl.name.lexeme}>"


@dataclass
class NativeFunction(LoxCallable):
    func: Callable[..., object]

    @property
    @override
    def arity(self):
        return len(inspect.signature(self.func).parameters)

    @override
    def __call__(self, _intr, args: list[object]):
        return self.func(*args)

    def __str__(self):
        # Would be more fun to also print native function __name__ but oh well...
        return "<native fn>"
