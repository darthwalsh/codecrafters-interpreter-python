from app.scanner import Token


class LoxRuntimeError(Exception):
    """Don't shadow builtin RuntimeError"""

    def __init__(self, token: Token, message: str):
        super().__init__(message)
        self.token = token
        self.message = message


class ReturnUnwind(Exception):
    def __init__(self, value: object, keyword: Token):
        self.value = value
        self.token = keyword
