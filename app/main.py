import sys

from app.scanner import Scanner, ScannerError

def main():
    if len(sys.argv) < 3:
        print("Usage: ./your_program.sh tokenize <filename>", file=sys.stderr)
        exit(1)

    command = sys.argv[1]
    filename = sys.argv[2]

    if command != "tokenize":
        print(f"Unknown command: {command}", file=sys.stderr)
        exit(1)

    with open(filename) as file:
        file_contents = file.read()

    print("Tokenizing", len(file_contents), "chars", file=sys.stderr)

    scanner = Scanner(file_contents)
    try:
        for token in scanner.scan_tokens():
            print(token)
    except ScannerError as e:
        print(f"Scanner error: {e}", file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    main()
