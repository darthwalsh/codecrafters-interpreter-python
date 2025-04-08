from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from app.func import LoxCallable, LoxFunction
from app.runtime import LoxRuntimeError
from app.scanner import Token
from app.scanner import TokenType as TT

if TYPE_CHECKING:  # pragma: no cover
    from app.interpreter import Interpreter

@dataclass
class LoxClass(LoxCallable):
    name: str
    methods: dict[str, LoxFunction]

    @property
    @override
    def arity(self):
        if init := self.methods.get("init"):
            return init.arity
        return 0

    @override
    def __call__(self, intr: "Interpreter", args: list[object]) -> object:
        instance = LoxInstance(self)
        if init := self.methods.get("init"):
            init.bind(instance)(intr, args)
        return instance

    def __str__(self):
        return self.name


class InitFunction(LoxFunction):
    @override
    def __call__(self, intr: "Interpreter", args: list[object]):
        # Can't just use super()() https://stackoverflow.com/a/72722823/771768
        super().__call__(intr, args)
        return self.closure[Token(TT.THIS, "this", -1, -1)]


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
        return m.bind(self)

    def __setitem__(self, name: Token, value: object):
        self.fields[name.lexeme] = value

    def __str__(self):
        return f"{self.clss.name} instance"
