from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override

from app.expression import (
    Assign,
    Binary,
    Call,
    Expr,
    Get,
    Grouping,
    Literal,
    Logical,
    Set,
    This,
    Unary,
    Variable,
    Visitor,
)
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
class Class(Stmt):
    name: Token
    methods: list["Function"]


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
    def visit_class(self, c: Class) -> T:
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


class BaseVisitor(Visitor[None], StmtVisitor[None]):
    @override
    def visit_block(self, block: Block) -> None:
        for st in block.statements:
            st.accept(self)

    @override
    def visit_class(self, c: Class) -> None:
        for m in c.methods:
            m.accept(self)

    @override
    def visit_expression(self, ex: Expression) -> None:
        ex.expr.accept(self)

    @override
    def visit_function(self, f: Function) -> None:
        for st in f.body:
            st.accept(self)

    @override
    def visit_if(self, i: If) -> None:
        i.condition.accept(self)
        i.then_branch.accept(self)
        if i.else_branch:
            i.else_branch.accept(self)

    @override
    def visit_return(self, ret: Return) -> None:
        if ret.value:
            ret.value.accept(self)

    @override
    def visit_print(self, pr: Print) -> None:
        pr.expr.accept(self)

    @override
    def visit_var(self, var: Var) -> None:
        if var.initializer:
            var.initializer.accept(self)

    @override
    def visit_while(self, w: While) -> None:
        w.condition.accept(self)
        w.body.accept(self)

    @override
    def visit_assign(self, assign: Assign) -> None:
        assign.value.accept(self)

    @override
    def visit_binary(self, binary: Binary) -> None:
        binary.left.accept(self)
        binary.right.accept(self)

    @override
    def visit_call(self, call: Call) -> None:
        call.callee.accept(self)
        for arg in call.args:
            arg.accept(self)

    @override
    def visit_get(self, get: Get) -> None:
        get.object.accept(self)

    @override
    def visit_grouping(self, grouping: Grouping) -> None:
        grouping.value.accept(self)

    @override
    def visit_literal(self, literal: Literal) -> None:
        pass

    @override
    def visit_logical(self, logical: Logical) -> None:
        logical.left.accept(self)
        logical.right.accept(self)

    @override
    def visit_set(self, set: Set) -> None:
        set.object.accept(self)
        set.value.accept(self)

    @override
    def visit_this(self, this: This) -> None:
        pass

    @override
    def visit_unary(self, unary: Unary) -> None:
        unary.right.accept(self)

    @override
    def visit_variable(self, variable: Variable) -> None:
        pass

    def accept_any(self, e: Expr | list[Stmt]) -> None:
        if isinstance(e, Expr):
            e.accept(self)
        else:
            for st in e:
                st.accept(self)
