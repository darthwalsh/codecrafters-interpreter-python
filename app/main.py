import os
import sys
from contextlib import contextmanager
from functools import cache

from app.ast import AstPrinter
from app.interpreter import Interpreter
from app.parser import Parser
from app.resolver import static_analysis
from app.runtime import LoxRuntimeError
from app.scanner import Scanner, Token
from app.scanner import TokenType as TT

LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70

MAX_ERRORS = 9000
CRAFTING_INTERPRETERS_COMPAT = os.getenv("CRAFTING_INTERPRETERS_COMPAT")

had_error = False


def count_errors():
    """HACK to quickly crash on infinite error loops"""
    global had_error
    for _ in range(MAX_ERRORS):
        had_error = True
        yield
    raise RuntimeError(f"ERRORS OVER {MAX_ERRORS}!!!")  # pragma: no cover


error_counter = count_errors()


def report(line: int, where: str, message: str):
    next(error_counter)
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)


def compile_error(token: Token, message: str):
    lexeme = f"'{token.lexeme}'" if token.type != TT.EOF else "end"
    report(token.line, f" at {lexeme}", message)


def runtime_error(e: LoxRuntimeError):
    next(error_counter)

    print(e.message, file=sys.stderr)
    print(f"[line {e.token.line}]", file=sys.stderr)


@cache
def verbose_stream():
    if CRAFTING_INTERPRETERS_COMPAT:
        return open(os.devnull, "w")
    return sys.stderr


@contextmanager
def step(stage, exit_code=LEXICAL_ERROR_CODE):
    """Run stage using stdout or stderr then exit on errors or command.
    Could conditionally use redirect_stdout but that seemed *too* magic.
    """
    header(stage)
    final = stage == command
    yield sys.stdout if final else verbose_stream()
    if had_error:
        sys.exit(exit_code)
    if final:
        sys.exit()
    print(file=verbose_stream())


def header(stage):
    print(f" {stage.upper()} ".center(20, "="), file=verbose_stream())


def main(source):
    scanner = Scanner(source, report)
    tokens = scanner.scan_tokens()

    with step("tokenize") as out:
        for token in tokens:
            print(token, file=out)

    parser = Parser(tokens, compile_error)

    if command in ("parse", "evaluate"):
        expr = parser.parse_expr()
        with step("parse") as out:
            if expr:
                print(AstPrinter().view(expr), file=out)
        if not expr:
            sys.exit("IMPOSSIBLE STATE: None returned without parse error")  # pragma: no cover

        with step("evaluate", exit_code=RUNTIME_ERROR_CODE) as out:
            Interpreter(runtime_error, out).interpret(expr)  # No Resolver for eval expression

    with step("parse_statement") as out:
        stmt = parser.parse_stmt()
        print(AstPrinter().view(stmt), file=out)

    with step("run", exit_code=RUNTIME_ERROR_CODE) as out:
        interpreter = Interpreter(runtime_error, out)
        with step("resolver"):
            static_analysis(interpreter, stmt, compile_error)
        interpreter.interpret(stmt)

    sys.exit(f"Unknown command: {command}")


if __name__ == "__main__":  # pragma: no cover
    if len(sys.argv) != 3:
        sys.exit("Usage: ./your_program.sh [tokenize|parse|evaluate|run] <filename>")

    _, command, filename = sys.argv

    with open(filename) as file:
        file_contents = file.read()
    main(file_contents)
