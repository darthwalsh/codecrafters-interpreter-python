from app.runtime import LoxRuntimeError
from app.scanner import Token


class Environment:
    def __init__(self):
        self.values: dict[str, object] = {}

    def __getitem__(self, name: Token):
        try:
            return self.values[name.lexeme]
        except KeyError:
            raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def __setitem__(self, key: str, value: object):
        self.values[key] = value

    def assign(self, name: Token, value: object):
        if (key := name.lexeme) in self.values:
            self[key] = value
        else:
            raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")
