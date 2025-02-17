from app import main

import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import requests
import yaml


def load_yaml():
    yaml_file = Path(tempfile.gettempdir()) / "interpreter-course-definition.yml"
    if not yaml_file.exists():
        print("Downloading!")
        url = "https://raw.githubusercontent.com/codecrafters-io/build-your-own-interpreter/main/course-definition.yml"
        response = requests.get(url)
        response.raise_for_status()
        yaml_file.write_text(response.text)
    print("Using", yaml_file)

    return yaml.safe_load(yaml_file.read_text())


ignored_stages = """
Scanning: Empty file
""".splitlines()


def get_stages():
    for stage in load_yaml()["stages"]:
        name = stage["name"]
        description = stage["description_md"]

        if name in ignored_stages:
            continue

        if "$ ./your_program.sh tokenize " not in description:
            # TODO not supported
            continue

        parsed = parse_markdown(description)
        if not parsed:
            raise ValueError(f"Failed to parse stage {name}")
        yield name, *parsed


def parse_markdown(description):
    # TODO this regex is too eager to match ``` then a lot of text, until finding the end of the pattern. Might work to change the first code block to something like ```[^\n]*\n((?:[^\n]|\n[^`])*?)\n``` or using forward negative to prevent parsing ``` as part of the code block...
    # OR, would be a *lot* easier to use a real markdown parser, and look for code block in the markdown AST... Maybe https://python-markdown.github.io/extensions/api/ or pandoc would be good starts
    pattern = r"For example, if `test.lox` contains the following:\n\n```[^\n]*\n(.*?)```\n\nThe tester will run your program like this:\n\n```[^\n]*\n\$ ./your_program.sh (\w+) test.lox\n(.*?)```"
    if match := re.search(pattern, description, re.DOTALL):
        return match.groups()

    ## TODO look for Test Case 1, 2, 3:

class LineMatcher:
    def __init__(self, file, prefix):
        self.file = file
        self.prefix = prefix
    def write(self, line):
        if line.startswith(self.prefix):
            self.file.write(line + "\n")

class TestCraft(unittest.TestCase):
    def check(self, command, source, code, out):
        """Returns actual stderr"""
        main.exit_code = 0
        main.command = command

        with redirect_stdout(io.StringIO()) as stdout:
            with redirect_stderr(LineMatcher(stdout, "[line")):
                try:
                    actual_code = 0
                    main.main(source)
                except SystemExit as e:
                    actual_code = e.code or 0

        self.assertEqual(actual_code, code)
        self.assertEqual(stdout.getvalue().strip(), out.strip())

    def test_all(self):
        for name, lox, cmd, output in get_stages():
            lox = lox.replace("<|TAB|>", "\t").replace("<|SPACE|>", " ")
            with self.subTest(name, cmd=cmd, lox=lox, output=output):
                print(name)
                exit_code = main.LEXICAL_ERROR_CODE if '[line ' in output else 0
                self.check(cmd, lox, exit_code, output)


if __name__ == "__main__":
    unittest.main()
