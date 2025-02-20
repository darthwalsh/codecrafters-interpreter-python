import inspect
from collections.abc import Callable


def shim(f: Callable, name: str, params: list[str]):
    f.__name__ = name

    # HACK this is CPython implementation detail: https://stackoverflow.com/a/56356583/771768
    f.__signature__ = build_signature(params)  # pyright: ignore [reportFunctionMemberAccess]
    # Don't use __text_signature__ because then python has to parse it


def build_signature(names: list[str]):
    kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
    return inspect.Signature([inspect.Parameter(name, kind) for name in names])


def arity(f):
    sig = inspect.signature(f)
    return len(sig.parameters)
