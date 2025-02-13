from contextlib import contextmanager
import sys

from app.interpreter import Interpreter
from app.parser import AstPrinter, Parser
from app.scanner import Scanner


LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70


had_error = False
def report(line, where, message):
    global had_error
    had_error = True
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)


@contextmanager
def step(stage, code):
    """Run block using stdout or stderr then exit on errors or command"""
    print(f" {stage.upper()} ".center(20, "="), file=sys.stderr)
    final = stage == command
    yield sys.stdout if final else sys.stderr
    if had_error:
        sys.exit(code)
    if final:
        sys.exit()
    print(file=sys.stderr)


def main():
    with open(filename) as file:
        file_contents = file.read()

    scanner = Scanner(file_contents, report)
    tokens = scanner.scan_tokens()

    with step("tokenize", LEXICAL_ERROR_CODE) as out:
        for token in tokens:
            print(token, file=out)

    parser = Parser(tokens, report)
    expr = parser.parse()
    with step("parse", LEXICAL_ERROR_CODE) as out:
        if expr:
            print(AstPrinter().print(expr), file=out)

    interpreter = Interpreter()
    with step("evaluate", RUNTIME_ERROR_CODE) as out:
        interpreter.interpret(expr, out)

    sys.exit(f"Unknown command: {command}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: ./your_program.sh [tokenize|parse|evaluate] <filename>")

    _, command, filename = sys.argv
    main()
