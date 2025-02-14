from app.environment import Environment
from app.runtime import ReturnUnwind
from app.statement import Function


class LoxFunction:  # MAYBE want this as an ABC that clock implements?
    def __init__(self, decl: Function):
        self.decl = decl
        self.arity = len(decl.params)
        self.__name__ = decl.name.lexeme

    def __call__(self, intr, args: list[object]):
        # MAYBE figure out circular type hint on intr: Interpreter
        env = Environment(intr.global_env)  # TODO for closures this changes
        for a, p in zip(args, self.decl.params, strict=True):
            env[p.lexeme] = a

        try:
            intr.execute_block(self.decl.body, env)
        except ReturnUnwind as e:
            return e.value

