import sys
import logging

from app.parser import AstPrinter, Parser
from app.scanner import Scanner, Error

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)


LEXICAL_ERROR_CODE = 65
RUNTIME_ERROR_CODE = 70


def main():
    if len(sys.argv) < 3:
        print("Usage: ./your_program.sh tokenize <filename>", file=sys.stderr)
        exit(1)

    _, command, filename = sys.argv
    with open(filename) as file:
        file_contents = file.read()

    scanner = Scanner(file_contents)
    tokens = scanner.scan_tokens()
    if command == "tokenize":
        for token in tokens:
            if isinstance(token, Error):
                print(token, file=sys.stderr)
            else:
                print(token)
        exit(scanner.has_error * LEXICAL_ERROR_CODE)
    else:
        for token in tokens:
            print(token, file=sys.stderr)
        print(file=sys.stderr)

    if command == "parse":
        parser = Parser(tokens)
        print(AstPrinter().print(parser.parse()))
        exit(parser.has_error * RUNTIME_ERROR_CODE)

    print(f"Unknown command: {command}", file=sys.stderr)
    exit(1)


if __name__ == "__main__":
    main()
