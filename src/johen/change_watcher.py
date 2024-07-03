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
    stack: "list[ChangeResult]" = dataclasses.field(default_factory=list)

    def __enter__(self) -> "ChangeResult":
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
        return NamedBool(f"{self.orig!r} was {value!r}", self.orig == value) & self.as_named_bool()

    def to_value(self, value: Any):
        return self.as_named_bool() & NamedBool(f"resulted in {value!r}", self.result == value)

    def remains(self, value: Any) -> NamedBool:
        return -self.as_named_bool() & NamedBool(f"resulted in {value!r}", self.result == value)

    def as_named_bool(self) -> NamedBool:
        assert (
            self.orig is not _unset
        ), "ChangeWatcher.__enter__ was not called, cannot compute result!"
        assert (
            self.result is not _unset
        ), "ChangeWatcher.__exit__ was not called, cannot compute result!"

        return NamedBool(f"{self.orig!r} changed to {self.result!r}", self.result != self.orig)

    def __bool__(self) -> bool:
        return bool(self.as_named_bool())

    def __str__(self) -> str:
        return str(self.as_named_bool())

    def repr(self) -> str:
        return f"ChangeWatcher({self.orig!r}, {self.result!r})"
