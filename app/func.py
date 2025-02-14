from dataclasses import dataclass
from app.environment import Environment
from app.runtime import ReturnUnwind
from app.statement import Function


@dataclass
class LoxFunction:  # MAYBE some ABC that clock implements?
    decl: Function
    closure: Environment

    @property
    def arity(self):
        return len(self.decl.params)

    @property
    def __name__(self):
        return self.decl.name.lexeme

    def __call__(self, intr, args: list[object]):
        # MAYBE figure out circular type hint on intr: Interpreter
        env = Environment(self.closure)
        for a, p in zip(args, self.decl.params, strict=True):
            env[p.lexeme] = a

        try:
            intr.execute_block(self.decl.body, env)
        except ReturnUnwind as e:
            return e.value
