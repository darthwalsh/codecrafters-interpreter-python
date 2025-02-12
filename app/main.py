import sys
import logging

from app.scanner import Scanner, Error

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)


LEXICAL_ERROR_CODE = 65


def main():
    if len(sys.argv) < 3:
        print("Usage: ./your_program.sh tokenize <filename>", file=sys.stderr)
        exit(1)

    _, command, filename = sys.argv

    if command == "tokenize":
        return tokenize(filename)
    print(f"Unknown command: {command}", file=sys.stderr)
    exit(1)

    tokenize(filename)


def tokenize(filename):
    with open(filename) as file:
        file_contents = file.read()

    logging.info(f"Tokenizing {len(file_contents)} chars")

    scanner = Scanner(file_contents)
    for token in scanner.scan_tokens():
        if isinstance(token, Error):
            print(token, file=sys.stderr)
        else:
            print(token)
    if scanner.has_error:
        sys.exit(LEXICAL_ERROR_CODE)


if __name__ == "__main__":
    main()
