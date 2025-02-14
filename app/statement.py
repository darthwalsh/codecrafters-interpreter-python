from dataclasses import dataclass

from abc import ABC, abstractmethod

from app.expression import Expr
from app.scanner import Token


class Stmt(ABC):
    def accept[T](self, visitor: "StmtVisitor[T]") -> T:
        """i.e. calls self.binary(self)"""
        subclass_name = self.__class__.__name__.lower()
        return getattr(visitor, f"visit_{subclass_name}")(self)


@dataclass(frozen=True)
class Expression(Stmt):
    expr: Expr


@dataclass(frozen=True)
class Print(Stmt):
    expr: Expr


@dataclass(frozen=True)
class Var(Stmt):
    name: Token
    initializer: Expr | None

class StmtVisitor[T](ABC):
    @abstractmethod
    def visit_expression(self, ex: Expression) -> T:
        pass

    @abstractmethod
    def visit_print(self, pr: Print) -> T:
        pass

    @abstractmethod
    def visit_var(self, var: Var) -> T:
        pass
