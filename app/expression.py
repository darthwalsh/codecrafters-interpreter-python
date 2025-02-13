from dataclasses import dataclass


from abc import ABC, abstractmethod

from app.scanner import Token


class Expr(ABC):
    def accept[T](self, visitor: "Visitor[T]") -> T:
        """i.e. calls self.binary(self)"""
        subclass_name = self.__class__.__name__.lower()
        return getattr(visitor, f"visit_{subclass_name}")(self)


@dataclass(frozen=True)
class Binary(Expr):
    left: Expr
    operator: Token
    right: Expr
    # Don't need @override accept() because it's dynamically dispatched in parent class
    # i.e. def accept(self, visitor: Visitor):
    #     return visitor.binary(self)


@dataclass(frozen=True)
class Grouping(Expr):
    value: Expr


@dataclass(frozen=True)
class Literal(Expr):
    value: object


@dataclass(frozen=True)
class Unary(Expr):
    operator: Token
    right: Expr


class Visitor[T](ABC):
    @abstractmethod
    def visit_binary(self, binary: Binary) -> T:
        pass

    @abstractmethod
    def visit_grouping(self, grouping: Grouping) -> T:
        pass

    @abstractmethod
    def visit_literal(self, literal: Literal) -> T:
        pass

    @abstractmethod
    def visit_unary(self, unary: Unary) -> T:
        pass
