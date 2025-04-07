from dataclasses import dataclass, field
from typing import override

from app.environment import Environment
from app.func import LoxCallable, LoxFunction
from app.runtime import LoxRuntimeError
from app.scanner import Token


@dataclass
class LoxClass(LoxCallable):
    name: str
    methods: dict[str, LoxFunction]

    @property
    @override
    def arity(self):
        return 0  # TODO(init)

    @override
    def __call__(self, _intr, _args) -> object:  # TODO(init) args: object
        instance = LoxInstance(self)
        if hasattr(self, "init"):
            raise NotImplementedError  # pragma: no cover  # TODO(init)
        return instance

    def __str__(self):
        return self.name


@dataclass
class LoxInstance:
    clss: LoxClass
    fields: dict[str, object] = field(default_factory=dict)

    def __getitem__(self, name: Token):
        try:
            # DONT use .get() because None is a valid value
            return self.fields[name.lexeme]
        except KeyError:
            pass
        try:
            m = self.clss.methods[name.lexeme]
        except KeyError:
            raise LoxRuntimeError(name, f"Undefined property '{name.lexeme}'.")
        wrapped = Environment(m.closure)
        wrapped["this"] = self
        return LoxFunction(m.decl, wrapped)

    def __setitem__(self, name: Token, value: object):
        self.fields[name.lexeme] = value

    def __str__(self):
        return f"{self.clss.name} instance"
