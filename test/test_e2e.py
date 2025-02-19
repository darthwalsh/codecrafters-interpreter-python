import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from app import main


class TestE2E(unittest.TestCase):
    def check(self, command, source, code, out, *errors):
        """Returns actual stderr"""
        main.exit_code = 0
        main.command = command

        with redirect_stdout(io.StringIO()) as f1:
            with redirect_stderr(io.StringIO()) as f2:
                try:
                    actual_code = 0
                    main.main(source)
                except SystemExit as e:
                    match e.code:
                        case None:
                            actual_code = 0
                        case str():
                            print(e.code, file=f2)
                            actual_code = 1
                        case _:
                            actual_code = e.code

        self.assertEqual(actual_code, code)
        self.assertEqual(f1.getvalue().strip(), out.strip())

        actual_errors = [line for line in f2.getvalue().splitlines() if line.startswith("[line")]
        self.assertSequenceEqual(actual_errors, errors)

        return f2.getvalue()

    def test_unknown(self):
        err = self.check(
            "foobar",
            "1.0;",
            1,
            "",
        )
        self.assertIn("Unknown command: foobar\n", err)

    def test_tokenize(self):
        self.check("tokenize", "1 nil", 0, "NUMBER 1 1.0\nNIL nil null\nEOF  null")

        self.check(
            "tokenize",
            "1 $",
            main.LEXICAL_ERROR_CODE,
            "NUMBER 1 1.0\nEOF  null",
            "[line 1] Error: Unexpected character: $",
        )

    def test_parse(self):
        self.check("parse", "1 + 1", 0, "(+ 1.0 1.0)")

        self.check(
            "parse",
            "1.2 1",
            main.LEXICAL_ERROR_CODE,
            "1.2",
            "[line 1] Error at '1': Expected end of expression",
        )

    def test_evaluate(self):
        self.check("evaluate", "1 + 1", 0, "2")

        err = self.check(
            "evaluate",
            "-nil",
            main.RUNTIME_ERROR_CODE,
            "",
            "[line 1]",
        )
        self.assertIn("Operand must be a number.\n[line 1]", err)

    def test_run(self):
        self.check("run", "print 1 + 1;", 0, "2")

        err = self.check(
            "run",
            "\n-nil;",
            main.RUNTIME_ERROR_CODE,
            "",
            "[line 2]",
        )
        self.assertIn("Operand must be a number.\n[line 2]", err)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
