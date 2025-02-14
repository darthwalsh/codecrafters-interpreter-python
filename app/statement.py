from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.expression import Expr
from app.scanner import Token


class Stmt(ABC):
    def accept[T](self, visitor: "StmtVisitor[T]") -> T:
        """i.e. calls self.binary(self)"""
        subclass_name = self.__class__.__name__.lower()
        return getattr(visitor, f"visit_{subclass_name}")(self)


@dataclass(frozen=True)
class Block(Stmt):
    statements: list[Stmt]


@dataclass(frozen=True)
class Expression(Stmt):
    expr: Expr


@dataclass(frozen=True)
class Function(Stmt):
    name: Token
    params: list[Token]
    body: list[Stmt]


@dataclass(frozen=True)
class If(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Stmt | None


@dataclass(frozen=True)
class Print(Stmt):
    expr: Expr


@dataclass(frozen=True)
class Return(Stmt):
    keyword: Token
    value: Expr | None


@dataclass(frozen=True)
class Var(Stmt):
    name: Token
    initializer: Expr | None


@dataclass(frozen=True)
class While(Stmt):
    condition: Expr
    body: Stmt


class StmtVisitor[T](ABC):
    @abstractmethod
    def visit_block(self, block: Block) -> T:
        pass

    @abstractmethod
    def visit_expression(self, ex: Expression) -> T:
        pass

    @abstractmethod
    def visit_function(self, f: Function) -> T:
        pass

    @abstractmethod
    def visit_if(self, i: If) -> T:
        pass

    @abstractmethod
    def visit_return(self, ret: Return) -> T:
        pass

    @abstractmethod
    def visit_print(self, pr: Print) -> T:
        pass

    @abstractmethod
    def visit_var(self, var: Var) -> T:
        pass

    @abstractmethod
    def visit_while(self, w: While) -> T:
        pass
