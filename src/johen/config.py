import datetime
import random
import uuid
import zlib
from typing import Any, Iterable, Iterator, Literal, Type

from johen.generators import base, specialized
from johen.generators.annotations import AnnotationMatcher
from johen.random import gen

__all__ = [
    "ParametrizeConfig",
    "get_base_config",
    "updated_config",
    "compile_matchers",
    "pick_seed_from_name",
]

try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict


class ParametrizeConfig(TypedDict, total=False):
    """
    Configures how the parametrize family of functions behave.
    """

    # Controls how the seed should be set before generating examples.  When None, a default strategy is taken based on
    # parameterize implementation, usually hashing the test function name.  This should be stable so that local and CI
    # test runs agree.
    seed: int | None
    # Configures the number of parametrized examples that should be generated.
    count: int
    # See `AnnotationProcessingContext.generate_defaults`
    generate_defaults: bool | Literal["holes"]
    # Which named arguments to actually parametrize -- useful for excluding arguments that are provided by the testing
    # framework, such as fixtures or mocks.
    arg_set: Iterable[str] | None
    # Overrides for named parameters, a shorthand for using Annotated[x, Examples(iterator)]
    overrides: dict[str, Iterable]

    # The maximum calls to `gen.__next__` allowed before yielding a value.  Note that thanks to the halting
    # problem, there is no perfect answer here -- it's at the intersection of every way *you* use generators.
    # Ideally there is a maximum depth at which you are generating, and you find that through experience.
    # Increasing this can hide bugs and performance issues.  Decreasing this can lead to fragile generation and
    # unexpected failures.
    max_iterations: int
    type_matchers: dict[Any, Iterator]
    matchers: list[AnnotationMatcher]
    globals: dict[str, Any]


def pick_seed_from_name(name: str) -> int:
    return zlib.crc32(name.encode("utf8")) & 0xFFFFFFFF


def compile_matchers(config: ParametrizeConfig) -> list[AnnotationMatcher]:
    return [
        *config["matchers"],
        lambda context: config["type_matchers"].get(context.source, None),
    ]


def get_base_config() -> ParametrizeConfig:
    return {
        "seed": None,
        "generate_defaults": False,
        "arg_set": None,
        "overrides": {},
        "max_iterations": 10000,
        "count": 10,
        "type_matchers": {
            int: specialized.ints,
            str: specialized.ascii_words,
            uuid.UUID: specialized.uuids,
            bool: specialized.bools,
            object: specialized.objects,
            float: specialized.valid_floats,
            bytes: specialized.byte_strings,
            datetime.date: specialized.dates,
            datetime.datetime: specialized.datetimes,
            datetime.timedelta: specialized.positive_timedeltas,
            None: specialized.nones,
            type(None): specialized.nones,
            Any: specialized.json_primitives,
            random.Random: (r for r in gen),
        },
        "matchers": [
            base.generate_dicts_from_typeddict,
            base.generate_lists_sets_frozen_sets,
            base.generate_named_tuples,
            base.generate_dataclass_instances,
            base.generate_forward_refs,
            base.generate_literals,
            base.generate_dicts,
            base.generate_unions,
            base.generate_annotated,
            base.generate_enums,
            base.generate_tuples,
            base.generate_unexpected_annotation,
        ],
        "globals": {},
    }


def updated_config(left: ParametrizeConfig, right: ParametrizeConfig) -> ParametrizeConfig:
    default = get_base_config()

    return {
        "seed": right.get("seed", left.get("seed")),
        "count": right.get("count", left.get("count", default["count"])),
        "generate_defaults": right.get(
            "generate_defaults", left.get("generate_defaults", default["generate_defaults"])
        ),
        "arg_set": right.get("arg_set", left.get("arg_set")),
        "overrides": right.get("overrides", left.get("overrides", default["overrides"])),
        "max_iterations": right.get(
            "max_iterations", left.get("max_iterations", default["max_iterations"])
        ),
        "type_matchers": {**left.get("type_matchers", {}), **right.get("type_matchers", {})},
        "matchers": [*right.get("matchers", []), *left.get("matchers", [])],
        "globals": {**left.get("globals", {}), **right.get("globals", {})},
    }
