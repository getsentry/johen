import dataclasses
import enum
import random
import typing
from random import Random

import pytest
import typing_extensions

from johen import gen, generate, global_config
from johen.config import compile_matchers
from johen.examples import Examples
from johen.exc import GenerationError
from johen.generators.annotations import AnnotationProcessingContext
from johen.generators.base import (
    FullArgSpec,
    generate_call_args_for_argspec,
    generate_dicts_for_annotations,
    generate_tuples,
)
from johen.generators.specialized import JsonDict, JsonValue, SimpleSymbol, ints
from johen.pytest import parametrize, sometimes


@parametrize
def test_generate_dicts_for_annotations(
    annotations: typing.Mapping[str, typing.Annotated[typing.Any, Examples((int, str))]],
    r: Random,
):
    defaults = r.sample(list(annotations.keys()), r.randint(0, len(annotations)))

    assert sometimes(not annotations)
    if annotations:
        assert sometimes(not defaults)

    context = AnnotationProcessingContext.from_source(annotations)
    context.generate_defaults = False
    context.matchers = compile_matchers(global_config)
    for i in range(10):
        d = next(generate_dicts_for_annotations(annotations, context, defaults))
        assert len(d) == len(annotations) - len(defaults)
        for k, v in annotations.items():
            if k not in defaults:
                assert isinstance(d[k], v)
            else:
                assert k not in d

    context.generate_defaults = "holes"
    for i in range(10):
        d = next(generate_dicts_for_annotations(annotations, context, defaults))
        assert len(d) >= len(annotations) - len(defaults)
        assert sometimes(len(d) < len(annotations))

        for k, v in annotations.items():
            assert sometimes(k not in d)
            if k in d:
                assert isinstance(d[k], v)

    context.generate_defaults = True
    for i in range(10):
        d = next(generate_dicts_for_annotations(annotations, context, defaults))
        for k, v in annotations.items():
            assert isinstance(d[k], v)


@parametrize
def test_generate_dicts_for_dataclass_model(
    annotations: typing.Mapping[SimpleSymbol, typing.Annotated[typing.Any, Examples((int, str))]],
    r: Random,
):
    a = r.randint(0, len(annotations))
    b = r.randint(a, len(annotations))
    defaults_with_factory = list(annotations.keys())[a:b]
    defaults_with_no_factory = list(annotations.keys())[b:]
    _default = object()
    d = dataclasses.make_dataclass(
        "test",
        [
            (k, annotation, _default)
            if k in defaults_with_no_factory
            else (k, annotation, dataclasses.field(default_factory=lambda: _default))
            if k in defaults_with_factory
            else (k, annotation)
            for k, annotation in annotations.items()
        ],
    )

    instance: typing.Any
    for instance in generate(d, count=10, generate_defaults="holes"):
        assert isinstance(instance, d)
        for k, annotation in annotations.items():
            val = getattr(instance, k)
            assert sometimes(val is _default)
            assert sometimes(isinstance(val, annotation))
            assert val is _default or isinstance(val, annotation)


@parametrize
def test_generate_dicts(
    typing_dict: typing.Dict[str, int],
    d: dict[str, int],
    mapping: typing.Mapping[str, int],
    mut_mapping: typing.MutableMapping[str, int],
):
    for val in (typing_dict, d, mapping, mut_mapping):
        assert isinstance(val, dict)
        assert all(isinstance(k, str) for k in val.keys())
        assert all(isinstance(v, int) for v in val.values())

    class mycustomdict(dict):
        pass

    with pytest.raises(GenerationError):
        generate(mycustomdict)


@parametrize(seed=5, count=30)
def test_generate_results_from_call_arg_spec_analysis(arg_spec: FullArgSpec, r: Random) -> None:
    arg_spec = FullArgSpec(
        kwonlydefaults={
            k: i
            for k, i in zip(
                random.sample(arg_spec.kwonlyargs, r.randint(0, len(arg_spec.kwonlyargs))), ints
            )
        }
        if arg_spec.kwonlydefaults is not None
        else None,
        defaults=arg_spec.defaults[: len(arg_spec.args)] if arg_spec.defaults is not None else None,
        **{k: v for k, v in arg_spec._asdict().items() if k not in ("kwonlydefaults", "defaults")},
    )

    assert sometimes(len(arg_spec.args) > 0)

    assert sometimes(arg_spec.varargs is None)
    if arg_spec.varargs is not None:
        assert sometimes(len(arg_spec.varargs) > 0)

    assert sometimes(arg_spec.varkw is None)
    assert sometimes(arg_spec.defaults is None)
    if arg_spec.defaults is not None:
        assert sometimes(len(arg_spec.defaults) > 0)

    assert sometimes(arg_spec.kwonlyargs)

    assert sometimes(arg_spec.kwonlydefaults is None)
    if arg_spec.kwonlydefaults is not None:
        assert sometimes(arg_spec.kwonlydefaults is not None)

    assert sometimes(arg_spec.annotations)

    num_defaults = len(arg_spec.defaults) if arg_spec.defaults is not None else 0
    num_kwd_defaults = len(arg_spec.kwonlydefaults) if arg_spec.kwonlydefaults is not None else 0

    args_without_defaults = ", ".join(
        f"{arg}: int" for arg in arg_spec.args[: len(arg_spec.args) - num_defaults]
    )
    args_with_defaults = ", ".join(
        f"{arg}: int = {repr(arg_spec.defaults[i]) if arg_spec.defaults else ''}"
        for i, arg in enumerate(arg_spec.args[len(arg_spec.args) - num_defaults :])
    )
    star_args = ""

    if arg_spec.varargs is None:
        if arg_spec.kwonlyargs:
            star_args = "*"
    else:
        star_args = f"*{arg_spec.varargs}"

    kw_args_without_defaults = ", ".join(
        f"{arg}: int"
        for arg in arg_spec.kwonlyargs
        if arg_spec.kwonlydefaults is None or arg not in arg_spec.kwonlydefaults
    )
    if arg_spec.kwonlydefaults:
        kw_args_with_defaults = ", ".join(
            f"{arg}: int = {repr(arg_spec.kwonlydefaults[arg])}"
            for arg in arg_spec.kwonlyargs
            if arg in arg_spec.kwonlydefaults
        )
    else:
        kw_args_with_defaults = ""
    kw_args = f"**{arg_spec.varkw}" if arg_spec.varkw is not None else ""

    param_def = ",".join(
        part
        for part in (
            args_without_defaults,
            args_with_defaults,
            star_args,
            kw_args_without_defaults,
            kw_args_with_defaults,
            kw_args,
        )
        if part
    )

    resulting_globals: dict = {}
    exec(
        f"""
def my_test_func(
    {param_def}
):
    return True
""",
        resulting_globals,
    )

    my_test_func = resulting_globals["my_test_func"]
    context = AnnotationProcessingContext.from_source(my_test_func)
    context.generate_defaults = False
    context.matchers = compile_matchers(global_config)
    for (args, kwds), _ in zip(generate_call_args_for_argspec(arg_spec, context), range(3)):
        assert my_test_func(*args, **kwds)
        assert len(args) == len(arg_spec.args) - num_defaults, (args, arg_spec, num_defaults)
        assert len(kwds) == len(arg_spec.kwonlyargs) - num_kwd_defaults

    context.generate_defaults = "holes"
    gen.restart_at(gen.last_seed)
    for (args, kwds), _ in zip(generate_call_args_for_argspec(arg_spec, context), range(3)):
        assert my_test_func(*args, **kwds)
        assert sometimes(len(args) < len(arg_spec.args))
        assert sometimes(len(kwds) < len(arg_spec.kwonlyargs))
        assert sometimes(len(args) == len(arg_spec.args) + (1 if arg_spec.varargs else 0))
        assert sometimes(len(kwds) == len(arg_spec.kwonlyargs) + (1 if arg_spec.varkw else 0))
        gen.restart_at_next_seed()


@parametrize
def test_generate_named_tuples(result: FullArgSpec):
    assert isinstance(result.args, list)
    assert isinstance(result.varargs, (str, type(None)))
    assert isinstance(result.varkw, (str, type(None)))
    assert isinstance(result.kwonlyargs, list)
    assert isinstance(result.kwonlydefaults, (dict, type(None)))
    assert isinstance(result.annotations, dict)


class TestIntEnum(enum.IntEnum):
    a = 1
    b = 2
    c = 3


class TestEnum(enum.Enum):
    a = "1"
    b = "2"
    c = "3"


@parametrize
def test_generate_enums(a: tuple[TestIntEnum, TestIntEnum], b: tuple[TestEnum, TestEnum]):
    assert all(v in TestIntEnum for v in a)
    assert all(v in TestEnum for v in b)
    assert sometimes(a[0] != a[1])
    assert sometimes(b[0] != b[1])


@parametrize
def test_generate_literals(a: typing.Literal["a"]):
    assert a == "a"


@parametrize
def test_dicts_from_typeddicts(
    annotations: typing.Mapping[SimpleSymbol, typing.Annotated[typing.Any, Examples((int, str))]],
    r: Random,
):
    total = bool(random.randint(0, 1))
    a = r.randint(0, len(annotations)) if not total else len(annotations)
    not_required = list(annotations.keys())[a:]

    use_typing_extensions = random.random() < 0.5
    assert sometimes(use_typing_extensions)

    if use_typing_extensions:
        d = typing_extensions.TypedDict(
            "test",
            {
                k: (
                    annotation
                    if k not in not_required
                    else typing_extensions.NotRequired[annotation]
                )
                for k, annotation in annotations.items()
            },
        )
    else:
        d = typing.TypedDict(
            "test",
            {
                k: (
                    annotation
                    if k not in not_required
                    else typing_extensions.NotRequired[annotation]
                )
                for k, annotation in annotations.items()
            },
        )

    for instance in generate(d, count=10, generate_defaults="holes"):
        assert isinstance(instance, dict)
        for k, annotation in annotations.items():
            assert sometimes(k not in instance)
            if k in instance:
                assert isinstance(instance[k], annotation)


@parametrize
def test_generate_tuples(r: Random):
    num_ints = r.randint(0, 2)
    num_strs = r.randint(0, 2)
    has_ellipsis = r.random() < 0.5
    use_typing = r.random() < 0.5

    assert sometimes(has_ellipsis)
    assert sometimes(use_typing)
    assert sometimes(num_ints)
    assert sometimes(num_strs)
    assert sometimes(num_ints and num_strs and has_ellipsis)

    if use_typing:
        context = AnnotationProcessingContext.from_source(typing.Tuple)
    else:
        context = AnnotationProcessingContext.from_source(tuple)

    context.matchers = compile_matchers(global_config)
    context.args = (int,) * num_ints
    context.args += (str,) * num_strs
    if has_ellipsis:
        context.args += (float, ...)

    for _ in range(10):
        v = next(generate_tuples(context))  # type: ignore
        assert isinstance(v, tuple)
        assert sometimes(not v)
        assert all(isinstance(i, int) for i in v[:num_ints])
        assert all(isinstance(i, str) for i in v[num_ints : num_ints + num_strs])

        if has_ellipsis:
            assert sometimes(len(v) > num_ints + num_strs)
            assert all(isinstance(i, float) for i in v[num_ints + num_strs :])
        elif num_ints or num_strs:
            assert len(v) == num_ints + num_strs
        else:
            assert sometimes(any(a != b for a, b in zip(v, v[1:])))


@parametrize(globals={"JsonValue": JsonValue, "JsonDict": JsonDict}, count=30)
def test_recursive_types(json: JsonValue):
    assert sometimes(isinstance(json, dict))
    if isinstance(json, dict):
        for k, v in json.items():
            assert sometimes(isinstance(v, dict))
            assert sometimes(isinstance(v, list))
    assert sometimes(isinstance(json, list))
    assert sometimes(isinstance(json, int))
    assert sometimes(isinstance(json, str))
    assert sometimes(isinstance(json, float))
