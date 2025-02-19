from app.runtime import LoxRuntimeError
from app.scanner import Token


class Environment:
    def __init__(self, parent: "Environment" = None):
        self.values: dict[str, object] = {}
        self.parent: Environment | None = parent

    def __getitem__(self, name: Token):
        try:
            return self.values[name.lexeme]
        except KeyError:
            if self.parent:
                return self.parent[name]
            raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")

    def __setitem__(self, key: str, value: object):
        self.values[key] = value

    def assign(self, name: Token, value: object):
        if (key := name.lexeme) in self.values:
            self[key] = value
        else:
            if not self.parent:
                raise LoxRuntimeError(name, f"Undefined variable '{name.lexeme}'.")
            self.parent.assign(name, value)
