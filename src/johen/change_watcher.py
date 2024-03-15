import dataclasses
import typing
from typing import Any

from johen.named_bool import NamedBool


class _Unset:
    pass


_unset = _Unset()


@dataclasses.dataclass
class change_watcher:
    cb: typing.Callable[[], Any]
    stack: list[Any] = dataclasses.field(default_factory=list)

    def __enter__(self):
        self.stack.append(ChangeResult(orig=self.cb()))
        return self.stack[-1]

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            return None

        self.stack.pop().result = self.cb()


@dataclasses.dataclass
class ChangeResult:
    orig: Any = _unset
    result: Any = _unset

    def from_value(self, value: Any):
        return NamedBool(f"{self} (expected from: {value!r})", bool(self and self.orig == value))

    def to_value(self, value: Any):
        return NamedBool(
            f"{self} (expected result: {value!r})", bool(self and self.result == value)
        )

    def __bool__(self) -> bool:
        assert (
            self.orig is not _unset
        ), "ChangeWatcher.__enter__ was not called, cannot compute result!"
        assert (
            self.result is not _unset
        ), "ChangeWatcher.__exit__ was not called, cannot compute result!"
        return self.result != self.orig

    def __str__(self) -> str:
        assert (
            self.orig is not _unset
        ), "ChangeWatcher.__enter__ was not called, cannot compute result!"
        assert (
            self.result is not _unset
        ), "ChangeWatcher.__exit__ was not called, cannot compute result!"
        return f"{self.orig!r} changed to {self.result!r}"

    __repr__ = __str__
