from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.scanner import Token


class Expr(ABC):
    def accept[T](self, visitor: "Visitor[T]") -> T:
        """i.e. calls self.binary(self)"""
        subclass_name = self.__class__.__name__.lower()
        return getattr(visitor, f"visit_{subclass_name}")(self)


@dataclass(frozen=True)
class Assign(Expr):
    name: Token
    value: Expr
    # Don't need @override accept() because it's dynamically dispatched in parent class
    # i.e. def accept(self, visitor: Visitor[T]):
    #     return visitor.visit_assign(self)


@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr


@dataclass(frozen=True)
class Call(Expr):
    callee: Expr
    paren: Token
    args: list[Expr]


@dataclass(frozen=True)
class Grouping(Expr):
    value: Expr


@dataclass(frozen=True)
class Literal(Expr):
    value: object


@dataclass(frozen=True)
class Logical(Expr):
    left: Expr
    operator: Token
    right: Expr


@dataclass(frozen=True)
class Unary(Expr):
    operator: Token
    right: Expr


@dataclass(frozen=True)
class Variable(Expr):
    name: Token


class Visitor[T](ABC):
    @abstractmethod
    def visit_assign(self, assign: Assign) -> T:
        pass

    @abstractmethod
    def visit_binary(self, binary: Binary) -> T:
        pass

    @abstractmethod
    def visit_call(self, call: Call) -> T:
        pass

    @abstractmethod
    def visit_grouping(self, grouping: Grouping) -> T:
        pass

    @abstractmethod
    def visit_logical(self, logical: Logical) -> T:
        pass

    @abstractmethod
    def visit_literal(self, literal: Literal) -> T:
        pass

    @abstractmethod
    def visit_unary(self, unary: Unary) -> T:
        pass

    @abstractmethod
    def visit_variable(self, variable: Variable) -> T:
        pass
