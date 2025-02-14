import unittest
from contextlib import contextmanager

from app.environment import Environment
from app.runtime import LoxRuntimeError
from app.scanner import Token, TokenType as TT


class Wrapper:
    """Easily set properties to write to Environment"""

    def __init__(self, env: Environment):
        self.__dict__["env"] = env

    def __getattr__(self, name: str):
        return self.env[Token(TT.IDENTIFIER, name, None, 0)]

    def __setattr__(self, key: str, value: object):
        self.env[key] = value

    def assign(self, name: str, value: object):
        return self.env.assign(Token(TT.IDENTIFIER, name, None, 0), value)


class TestEnvironment(unittest.TestCase):
    def parent(self, **expected_parent):
        """small builder pattern for setting up parent/child with expected values"""

        class Child:
            def __init__(self, tc):
                self.tc = tc

            @contextmanager
            def child(self, **expected_child):
                parent = Wrapper(Environment())
                child = Wrapper(Environment(parent.env))
                yield parent, child

                self.tc.assertEqual(parent.env.values, expected_parent)
                self.tc.assertEqual(child.env.values, expected_child)

        return Child(self)

    def test_var(self):
        with self.parent().child(a=2) as (p, c):
            c.a = 2

        with self.parent(a=2).child() as (p, c):
            p.a = 2

        with self.parent(a=2).child(a=3) as (p, c):
            p.a = 2
            c.a = 3

        with self.parent(a=2).child(a=3) as (p, c):
            c.a = 3
            p.a = 2

    def test_get(self):
        with self.parent(a=3, b=5).child(a=2, b=6) as (p, c):
            with self.assertRaises(LoxRuntimeError):
                c.a

            c.a = 2
            self.assertEqual(c.a, 2)

            with self.assertRaises(LoxRuntimeError):
                p.a

            p.a = 3
            self.assertEqual(c.a, 2)
            self.assertEqual(p.a, 3)

            p.b = 5
            self.assertEqual(c.b, 5)
            self.assertEqual(p.b, 5)

            c.b = 6
            self.assertEqual(c.b, 6)
            self.assertEqual(p.b, 5)

    def test_assign(self):
        with self.parent().child() as (p, c):
            with self.assertRaises(LoxRuntimeError):
                c.assign("a", 2)

        with self.parent(a=2).child() as (p, c):
            p.a = 1
            c.assign("a", 2)
