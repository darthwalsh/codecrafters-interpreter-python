from contextlib import contextmanager
import sys

from app.ast import AstPrinter
from app.interpreter import Interpreter
from app.parser import Parser
from app.scanner import Scanner


LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70


exit_code = 0


def report(line, where, message):
    global exit_code
    exit_code = LEXICAL_ERROR_CODE
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)


def runtime_error(e):
    global exit_code
    exit_code = RUNTIME_ERROR_CODE
    print(e.message, file=sys.stderr)
    print(f"[line {e.token.line}]", file=sys.stderr)


@contextmanager
def step(stage):
    """Run block using stdout or stderr then exit on errors or command"""
    print(f" {stage.upper()} ".center(20, "="), file=sys.stderr)
    final = stage == command
    yield sys.stdout if final else sys.stderr
    if exit_code:
        sys.exit(exit_code)
    if final:
        sys.exit()
    print(file=sys.stderr)


def main(source):
    scanner = Scanner(source, report)
    tokens = scanner.scan_tokens()

    with step("tokenize") as out:
        for token in tokens:
            print(token, file=out)

    parser = Parser(tokens, report)
    expr = parser.parse()
    with step("parse") as out:
        if expr:
            print(AstPrinter().print(expr), file=out)

    interpreter = Interpreter(runtime_error)
    with step("evaluate") as out:
        interpreter.interpret(expr, out)

    sys.exit(f"Unknown command: {command}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: ./your_program.sh [tokenize|parse|evaluate] <filename>")

    _, command, filename = sys.argv

    with open(filename) as file:
        file_contents = file.read()
    main(file_contents)
