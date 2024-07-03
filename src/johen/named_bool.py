import dataclasses
from typing import Any


@dataclasses.dataclass
class NamedBool:
    message: str
    result: bool

    def __bool__(self):
        return self.result

    def __str__(self):
        return self.message

    def __and__(self, other: Any) -> Any:
        if not isinstance(other, NamedBool):
            return bool(self) and other
        return NamedBool(f"{self} and {other.message}", self.result and other.result)

    def __or__(self, other: Any) -> Any:
        if not isinstance(other, NamedBool):
            return bool(self) or other
        return NamedBool(f"{self} or {other.message}", self.result or other.result)

    def __neg__(self) -> "NamedBool":
        return NamedBool(f"not {self.message}", not self.result)

    def no(self) -> "NamedBool":
        return NamedBool(f"not {self.message}", not self.result)

    __repr__ = __str__
