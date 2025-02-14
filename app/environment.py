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

    def __setitem__(self, key, value):
        self.values[key] = value
