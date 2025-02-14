[![progress-banner](https://backend.codecrafters.io/progress/interpreter/5ed16121-3c0b-470d-895b-ae98cca3fb6d)](https://app.codecrafters.io/users/codecrafters-bot?r=2qF)

Completed extensions:
- [x] Parsing Expressions
- [x] Evaluating Expressions
- [x] Statements & State
- [x] Control Flow
- [x] Functions

## Challenge

This my Python solutions to the ["Build your own Interpreter" Challenge](https://app.codecrafters.io/courses/interpreter/overview). It follows the book [Crafting Interpreters](https://craftinginterpreters.com/) by Robert Nystrom.

In this challenge you'll build an interpreter for [Lox](https://craftinginterpreters.com/the-lox-language.html), a simple scripting language. Along the way, you'll learn about tokenization, ASTs, tree-walk interpreters and more. There is a [Java implemenation](https://github.com/munificent/craftinginterpreters/blob/4a840f70f69c6ddd17cfef4f6964f8e1bcd8c3d4/java/com/craftinginterpreters/lox/Lox.java#L23) on the book's repo (and C too!) which are easy to run locally if you want to 

## Running program

1. Ensure you have `python (3.12)` installed locally
2. Run `./your_program.sh` to run your program, which is implemented in `app/main.py`.

## Things I'm proud of
- Pretty decent unit tests for scanner, parser, interpreter, and main modules
- `AstPrinter` can print debug versions of all syntax, helps with dangling-else test
- `LoxFunction` models a Lox function as a normal python function
	- [ ] Should be possible to remove entirely, but want to check ahead in the book first...
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
- `main` uses a `with step("parse") as out: ...` context manager
	- The CLI options `tokenize|parse|evaluate|run` kind of follow a linear flow, so would take `O(N^2)` steps to represent each in their own function.
	- that exits if there were errors or `parse` was requested as the CLI result.
	- Use `print(..., file=out)` to write to `stderr` unless this was the requested text.
- [`test_environment`](test/test_environment.py) is an Environment wrapper allowing for `wrap.a = 1` to set `"a"` in the env.
	- Also context manager: `with self.parent(a=2).child() as (p, c): p.a = 1; c.assign("a", 2)` 
	-  Use `**kw_args`  for expected final parent/child env state instead of literal dicts.
`
## Bugs
- [ ] Have yet to implement [Chapter 11](https://craftinginterpreters.com/resolving-and-binding.html) onwards
- [ ] main script errors out if there are compiler/runtime 9000 errors.
## Extra ideas
- Add mypy or pylance full type checking?
- Refactor dozens of the `e = parse(); assert_match(SEMICOLON); return e`
	- i.e. context manager `with after(SEMICOLON): return e` should work the same?
- Runner 
- Use my [JustAnotherYamlParser](https://github.com/darthwalsh/JustAnotherYamlParser) BNF evaluator
	- I think it would produce the exact [Parse Tree](https://craftinginterpreters.com/representing-code.html#implementing-syntax-trees) so we would need a light tree-transform into a workaround AST
	- Could probably delete much of the Token / TokenType / Scanner / Parser modules?
	- BUT, could you get most of the same errors? Would want to check test_parser coverage.
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
