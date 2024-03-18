import contextlib
from typing import Any, Callable, Iterator, Literal, Type, TypeVar, cast, overload

from johen.config import ParametrizeConfig, compile_matchers, get_base_config
from johen.generators.annotations import AnnotationMatcher, AnnotationProcessingContext
from johen.random import gen

global_config: ParametrizeConfig = get_base_config()

_A = TypeVar("_A")


@overload
def generate(
    obj: Type[_A],
    generate_defaults: bool | Literal["holes"] | None = None,
    matchers: list[AnnotationMatcher] | None = None,
    seed: int | None = None,
    count: int | None = None,
    globals: dict[str, Any] | None = None,
) -> Iterator[_A]:
    ...


@overload
def generate(
    obj: Callable[..., _A],
    generate_defaults: bool | Literal["holes"] | None = None,
    matchers: list[AnnotationMatcher] | None = None,
    seed: int | None = None,
    count: int | None = None,
    globals: dict[str, Any] | None = None,
) -> Iterator[_A]:
    ...


@overload
def generate(
    obj: Any,
    generate_defaults: bool | Literal["holes"] | None = None,
    matchers: list[AnnotationMatcher] | None = None,
    seed: int | None = None,
    count: int | None = None,
    globals: dict[str, Any] | None = None,
) -> Iterator:
    ...


def generate(
    obj: Any,
    generate_defaults: bool | Literal["holes"] | None = None,
    matchers: list[AnnotationMatcher] | None = None,
    seed: int | None = None,
    count: int | None = None,
    globals: dict[str, Any] | None = None,
) -> Iterator:
    context = AnnotationProcessingContext.from_source(obj)

    if generate_defaults is not None:
        context.generate_defaults = generate_defaults
    else:
        context.generate_defaults = global_config["generate_defaults"]

    if matchers is not None:
        context.matchers = [*matchers, *compile_matchers(global_config)]
    else:
        context.matchers = compile_matchers(global_config)

    if globals is not None:
        context.globals = {**global_config["globals"], **globals}
    else:
        context.globals = global_config["globals"]

    if seed is not None:
        gen.restart_at(seed=seed)

    if count is not None:
        result = [i for i, _ in zip(context.generate(), range(count))]
        assert len(result) == count, f"Could not generate {count} values for {obj}"
        return iter(result)

    gen.remaining_iterations = global_config["max_iterations"]
    return context.generate()


@contextlib.contextmanager
def replace_global_config(new_config: ParametrizeConfig):
    orig = global_config.copy()
    cast(dict, global_config).clear()
    global_config.update(new_config)
    try:
        yield
    finally:
        cast(dict, global_config).clear()
        global_config.update(orig)
