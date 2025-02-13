import sys

from app.parser import AstPrinter, Parser
from app.scanner import Scanner


LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70


had_error = False
def report(line, where, message):
    global had_error
    had_error = True
    print(f"[line {line}] Error{where}: {message}", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print("Usage: ./your_program.sh tokenize <filename>", file=sys.stderr)
        exit(1)

    _, command, filename = sys.argv
    with open(filename) as file:
        file_contents = file.read()

    scanner = Scanner(file_contents, report)
    tokens = scanner.scan_tokens()

    if command == "tokenize":
        for token in tokens:
            print(token)
        exit(had_error * LEXICAL_ERROR_CODE)
    if had_error:
        exit(LEXICAL_ERROR_CODE)

    for token in tokens:
        print(token, file=sys.stderr)
    print(file=sys.stderr)

    parser = Parser(tokens, report)
    expr = parser.parse()
    if had_error:
        exit(LEXICAL_ERROR_CODE)

    if command == "parse":
        print(AstPrinter().print(expr))
        return

    print(f"Unknown command: {command}", file=sys.stderr)
    exit(1)


if __name__ == "__main__":
    main()
