[![progress-banner](https://backend.codecrafters.io/progress/interpreter/5ed16121-3c0b-470d-895b-ae98cca3fb6d)](https://app.codecrafters.io/users/codecrafters-bot?r=2qF)

Completed extensions:
- [x] Parsing Expressions
- [x] Evaluating Expressions
- [x] Statements & State
- [x] Control Flow
- [x] Functions
- [x] Resolving
- [x] Classes
- [ ] Inheritance

## Challenge

This my Python solutions to the ["Build your own Interpreter" Challenge](https://app.codecrafters.io/courses/interpreter/overview). It follows the book [Crafting Interpreters](https://craftinginterpreters.com/) by Robert Nystrom.

In this challenge you'll build an interpreter for [Lox](https://craftinginterpreters.com/the-lox-language.html), a simple scripting language. Along the way, you'll learn about tokenization, ASTs, tree-walk interpreters and more. There is a [Java implementation](https://github.com/munificent/craftinginterpreters/blob/4a840f70f69c6ddd17cfef4f6964f8e1bcd8c3d4/java/com/craftinginterpreters/lox/Lox.java#L23) on the book's repo (and C too!) which are easy to run locally if you want to compare behavior or run test suite against your own implementation (see below).

## Running program

1. Ensure you have `python (3.12)` installed locally
1. Run `./your_program.sh` to run your program, which is implemented in `app/main.py`.
1. Run tests with `pipenv run tests`
1. Assert 100% coverage with `pipenv run cov`
1. Format and lint code using [`ruff`](https://github.com/astral-sh/ruff) using `pipenv run fmt`
1. Type check with [`pyright`](https://microsoft.github.io/pyright) using `pipenv run check`

## Things I'm proud of
- Pretty decent unit tests for scanner, parser, interpreter, and main modules
- `AstPrinter` can print debug versions of all syntax, helps with dangling-else test
- `Expr` has pretty minimal boilerplate, didn't need to write a source code generator!
	- Creating e.g. `Assign` record class makes great use of `dataclass`
	- Instead of repeated static definitions:
		- e.g. `class Assign: def accept(self, v): return v.visit_assign(self)`
		- base class `accept()` uses dynamic dispatch to invoke `v["visit_{name}](self)`
	- But, kept the generic `Visitor[T]` static definitions `def visit_assign(self, assign: Assign) -> T:` for IDE support (I can't image defining these dynamically would play well with IDE type inference
- `Scanner` and `Parser`
	- Makes them easy to unit test
	- `Interpreter` takes an `IO` object to `print` to, making it pretty easy to test
- `Scanner` uses `IntEnum` 
	- to determine which range are keywords, using the enum name as string to match. i.e. `/print/` appears one time in file.
	- Also, uses the fact that e.g. `TokenType.BANG + 1 == TokenType.BANG_EQUAL` in a clever way
- `Parser` uses a better `private Token match(...)` pattern to combing predicate and `previous()`
	- `take_binary` make short work for `logic_and -> equality -> comparison -> ...`
- `Resolver` takes multiple passes of the syntax tree to find problems, which is much simpler than a do-everything class.
- `main` uses a `with step("parse") as out: ...` context manager
	- The CLI options `tokenize|parse|evaluate|run` kind of follow a linear flow, so would take `O(N^2)` steps to represent each in their own function.
	- that exits if there were errors or `parse` was requested as the CLI result.
	- Use `print(..., file=out)` to write to `stderr` unless this was the requested text.
- [`test_environment`](test/test_environment.py) is an Environment wrapper allowing for `wrap.a = 1` to set `"a"` in the env.
	- Also context manager: `with self.parent(a=2).child() as (p, c): p.a = 1; c.assign("a", 2)` 
	-  Use `**kw_args` for expected final parent/child env state instead of literal dicts.
- Book and CodeCrafters had some subtle differences in behavior; ust search code for `CRAFTING_INTERPRETERS()`

### Changes which didn't work out
- ~~`func` models a Lox function as a normal python function. Removed LoxFunction entirely in d70adfb.~~
	- In order to support `this`, we need to compose the function's environment with an outer environment with `this`.
    - Instead of having a function, now we need to put captured variables in an format that can be accessed (a class instance with fields).
- Tried to compose `LoxFunction` for `init()` returning `this` but ended up with a subclass as the "simplest" solution

## Bugs
- [ ] main script errors out if there are compiler/runtime 9000 errors.
## Extra ideas
- Use my [JustAnotherYamlParser](https://github.com/darthwalsh/JustAnotherYamlParser) BNF evaluator
	- I think it would produce the exact [Parse Tree](https://craftinginterpreters.com/representing-code.html#implementing-syntax-trees) so we would need a light tree-transform into a workaround AST
	- Could probably delete much of the Token / TokenType / Scanner / Parser modules?
	- BUT, could you get most of the same errors? 
        - [x] Would want to check test_parser coverage.
	- Could this take the AST and generate the datatypes and visitor interface?
- How hard would it be to "just" enable FFI in a similar way to c# with decorators?
```csharp
[DllImport("libc.so")]
private static extern int getpid();

[DllImport("user32.dll", SetLastError=true)]
static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
```

implementation in python might look like what ChatGPT generated:
```python
import ctypes
import ctypes.wintypes

libc = ctypes.CDLL("libc.so")
getpid = libc.getpid
getpid.restype = ctypes.c_int  # Return type is int (ctypes default)

user32 = ctypes.WinDLL("user32.dll", use_last_error=True)
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowThreadProcessId.argtypes = [ctypes.wintypes.HWND, ctypes.POINTER(ctypes.wintypes.DWORD)]
GetWindowThreadProcessId.restype = ctypes.wintypes.UINT
```

### Test cases from the codecrafters course definition
*See branch https://github.com/darthwalsh/codecrafters-interpreter-python/tree/wip-test-codecrafters-course*
- [-] Parse the course definition locally, and make script to run the input/output test cases?? ❌ 2025-02-17

Running all test cases can be kind of slow. Compare running a trivial program from 
* E2E tests that `imports main`; 50 microseconds
* `python3.12 -m app.main run`: 400 milliseconds
* `pipenv run python3.12 -m app.main`: 800 milliseconds = 10,000x slower to add pipenv and python overheads!

Also writing tests by hand can be a drag, so I had the idea to run smoke tests from [github.com/codecrafters-io/build-your-own-interpreter course-definition.yml](https://github.com/codecrafters-io/build-your-own-interpreter/blob/0fc863d1f4389d34705bf8529eff0a6d60127e15/course-definition.yml#L5105) (MIT License)

Instead of invoking their test runner which takes an entire second per test case, I could have a python in-process loop that executes all tests "instantly" like this:
1. Add requests and pyyaml to Pipfile `dev-packages` which seems not to break the official test runner
2. Test runner downloads and caches `course-definition.yml`
3. Parse YAML file for `.description_md`
4. Parse the markdown (see branch TODO comments, got stuck making this robust)
5. Load state from disk of course N expected to pass
6. Execute test cases that are known to pass: course 1 through course N
7. Attempt to pass course N+1, N+2, etc. which affects disk-state but not test-case result status
8. Would be great to have these tests results from a file-tree-watcher

Other sources for test cases:
- figure out how to use https://github.com/codecrafters-io/interpreter-tester repo (not OSS) for testing: it has [this template](https://github.com/codecrafters-io/interpreter-tester/blob/2d0a2ab76a8524481af1442ab0f05e7383bca876/test_programs/c4/2.lox) or [this ANSI output](https://github.com/codecrafters-io/interpreter-tester/blob/2d0a2ab76a8524481af1442ab0f05e7383bca876/test_programs/c4/2.lox), which also has a [golang Lox golden implementation](https://github.com/codecrafters-io/interpreter-tester/blob/2d0a2ab76a8524481af1442ab0f05e7383bca876/internal/lox/parser.go)...
- https://github.com/codecrafters-io/course-sdk might be useful for running a course locally

### Test cases from the Crafting Interpreters book
Based on https://github.com/munificent/craftinginterpreters/issues/1122 install dart 2:
```
brew install dart@2.12
brew unlink dart && brew link dart@2.12
```

Run `git clone github.com:munificent/craftinginterpreters.git`

Create an executable in craftinginterpreters folder
```bash
#!/bin/bash

arg=$(realpath $1)

cd /Users/walshca/code/codecrafters-interpreter-python
export CRAFTING_INTERPRETERS_COMPAT=1
exec python3 -m app.main run $arg
```

Run tests through implemented chapter:
```bash
dart tool/bin/test.dart chap12_classes --interpreter run.sh
```
