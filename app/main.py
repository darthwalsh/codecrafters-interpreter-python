from contextlib import contextmanager
import sys

from app.ast import AstPrinter
from app.interpreter import Interpreter
from app.parser import Parser
from app.scanner import Scanner


LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70

MAX_ERRORS = 9000


exit_code = 0


def count_errors():
    """HACK to quickly crash on infinite error loops"""
    for _ in range(MAX_ERRORS):
        yield
    raise RuntimeError(f"ERRORS OVER {MAX_ERRORS}!!!")


error_counter = count_errors()


def report(line, where, message):
    global exit_code
    next(error_counter)

    exit_code = LEXICAL_ERROR_CODE
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)


def runtime_error(e):
    global exit_code
    next(error_counter)

    exit_code = RUNTIME_ERROR_CODE
    print(e.message, file=sys.stderr)
    print(f"[line {e.token.line}]", file=sys.stderr)


@contextmanager
def step(stage):
    """Run block using stdout or stderr then exit on errors or command"""
    header(stage)
    final = stage == command
    yield sys.stdout if final else sys.stderr
    if exit_code:
        sys.exit(exit_code)
    if final:
        sys.exit()
    print(file=sys.stderr)


def header(stage):
    print(f" {stage.upper()} ".center(20, "="), file=sys.stderr)


def main(source):
    scanner = Scanner(source, report)
    tokens = scanner.scan_tokens()

    with step("tokenize") as out:
        for token in tokens:
            print(token, file=out)

    parser = Parser(tokens, report)

    if command in ("parse", "evaluate"):
        expr = parser.parse_expr()
        with step("parse") as out:
            if expr:
                print(AstPrinter().print(expr), file=out)

        with step("evaluate") as out:
            Interpreter(runtime_error, out).interpret(expr)

    header("parse statement")
    stmt = parser.parse_stmt()
    print(AstPrinter().print(stmt), file=sys.stderr)
    print(file=sys.stderr)

    with step("run") as out:
        Interpreter(runtime_error, out).interpret(stmt)

    sys.exit(f"Unknown command: {command}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: ./your_program.sh [tokenize|parse|evaluate|run] <filename>")

    _, command, filename = sys.argv

    with open(filename) as file:
        file_contents = file.read()
    main(file_contents)
