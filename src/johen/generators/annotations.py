import dataclasses
import inspect
import typing
from typing import Any, Iterator

from johen.exc import GenerationError
from johen.random import gen

_A = typing.TypeVar("_A")


class AnnotationMatcher(typing.Protocol):
    def __call__(self, context: "AnnotationProcessingContext") -> Iterator[Any] | None:
        ...


@dataclasses.dataclass
class AnnotationProcessingContext:
    source: Any
    origin: Any | None
    args: tuple[Any, ...]
    path: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    generate_defaults: bool | typing.Literal["holes"] = False
    matchers: list[AnnotationMatcher] = dataclasses.field(default_factory=list)
    globals: dict[str, Any] = dataclasses.field(default_factory=dict)
    recursive_depth: int = 0

    def concretely_implements(self, other: Any) -> bool:
        for origin in (self.origin, self.source):
            if origin is None or not inspect.isclass(origin):
                continue
            return issubclass(origin, other)
        return False

    def wrap_with_debug_context(self, iterator: Iterator[_A]) -> Iterator[_A]:
        def wrapper():
            try:
                for i in iterator:
                    yield i
            except Exception as e:
                raise GenerationError(
                    f"Generation failed unexpectedly for {' '.join(self.path)} {self.source}"
                ) from e

        return wrapper()

    def concretely_implemented_by(self, other: Any) -> bool:
        for origin in (self.origin, self.source):
            if origin is None:
                continue
            try:
                return issubclass(other, origin)
            except TypeError:
                continue
        return False

    def step(
        self,
        source: Any,
        step: str | None = None,
        args: tuple[Any, ...] | None = None,
        recursive=False,
    ) -> Iterator:
        next_context = AnnotationProcessingContext.from_source(source)
        if args is not None:
            next_context.origin = source
            next_context.args = args
        next_context.path = (*self.path, step) if step else self.path
        next_context.generate_defaults = self.generate_defaults
        next_context.matchers = self.matchers
        next_context.globals = self.globals
        if recursive:
            next_context.recursive_depth = self.recursive_depth + 1

        return next_context.generate()

    @classmethod
    def from_source(cls, source: Any) -> "AnnotationProcessingContext":
        return AnnotationProcessingContext(
            source=source,
            origin=typing.get_origin(source),
            args=typing.get_args(source) or (),
            path=(repr(source),),
        )

    def generate(
        self,
    ) -> typing.Iterator:
        for matcher in self.matchers:
            result = matcher(self)
            if result is not None:
                return result
        raise GenerationError(f"Could not generate for {' '.join(self.path)} {self.source}")
