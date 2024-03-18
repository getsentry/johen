import dataclasses
import enum
import inspect
import itertools
import types
import typing
from typing import Any, Iterator, get_type_hints

from johen.examples import Examples
from johen.exc import GenerationError
from johen.generators.annotations import AnnotationProcessingContext
from johen.generators.specialized import SimpleSymbol, ints
from johen.random import gen

__all__ = [
    "generate_dicts",
    "generate_enums",
    "generate_lists_sets_frozen_sets",
    "generate_tuples",
    "generate_unions",
    "generate_annotated",
    "generate_literals",
    "generate_dicts_for_annotations",
    "generate_dataclass_instances",
    "generate_unexpected_annotation",
    "generate_dicts_for_dataclass_model",
    "generate_call_args_for_argspec",
    "generate_results_from_call",
    "generate_dicts_from_typeddict",
    "generate_named_tuples",
]


def generate_dicts_for_annotations(
    annotations: typing.Mapping[str, int],
    context: "AnnotationProcessingContext",
    optional_keys: list[str],
) -> Iterator[dict[str, Any]]:
    generators: dict[str, Iterator[Any]] = {
        k: context.step(v, k)
        for k, v in annotations.items()
        if context.generate_defaults or k not in optional_keys
    }

    if not generators:
        return ({} for _ in gen)

    for k, v in generators.items():
        assert hasattr(v, "__next__")

    sampled_keys: Iterator[list[str]]
    if context.generate_defaults == "holes":
        sampled_keys = (r.sample(optional_keys, r.randint(0, len(optional_keys))) for r in gen)
    elif context.generate_defaults:
        sampled_keys = itertools.repeat(optional_keys)
    else:
        sampled_keys = itertools.repeat([])

    return (
        dict(
            (k, v)
            for k, v in zip(generators.keys(), values)
            if k not in optional_keys or k in included_keys
        )
        for values, included_keys in zip(zip(*generators.values()), sampled_keys)
    )


def generate_dicts_for_dataclass_model(
    context: "AnnotationProcessingContext",
) -> Iterator[dict[str, Any]]:
    hints = get_type_hints(context.source, include_extras=True)
    fields = {f.name: f for f in dataclasses.fields(context.source)}
    return generate_dicts_for_annotations(
        {k: hints.get(k, Any) for k, field in fields.items()},
        context,
        optional_keys=[k for k, field in fields.items() if _dataclass_has_default(field)],
    )


class FullArgSpec(typing.NamedTuple):
    args: list[SimpleSymbol]
    varargs: SimpleSymbol | None
    varkw: SimpleSymbol | None
    defaults: tuple[typing.Annotated[Any, Examples(ints)], ...] | None
    kwonlyargs: list[SimpleSymbol]
    kwonlydefaults: dict[SimpleSymbol, typing.Annotated[Any, Examples(ints)]] | None
    annotations: dict[str, typing.Annotated[Any, Examples((int,))]]


def generate_call_args_for_argspec(
    source: FullArgSpec, context: "AnnotationProcessingContext"
) -> typing.Iterator[tuple[tuple[Any, ...], dict[str, Any]]]:
    num_arg_defaults = len(source.defaults) if source.defaults is not None else 0

    required_args: list[Iterator[Any]] = []
    non_required_args: list[Iterator[Any]] = []
    for i, argname in enumerate(source.args):
        arg_iter = context.step(source.annotations.get(argname, Any), argname)
        if i < (len(source.args) - num_arg_defaults):
            required_args.append(arg_iter)
        elif context.generate_defaults:
            non_required_args.append(arg_iter)

    arg_generator: Iterator[tuple[Any, ...]]
    if required_args:
        arg_generator = zip(*required_args)
    else:
        arg_generator = itertools.repeat(tuple())

    if context.generate_defaults and non_required_args:
        arg_generator = (
            (
                *required,
                *(
                    non_required
                    if context.generate_defaults is True
                    else non_required[: r.randint(0, len(non_required))]
                ),
            )
            for required, non_required, r in zip(arg_generator, zip(*non_required_args), gen)
        )

    if source.varargs and context.generate_defaults:
        star_args_generator = context.step(
            tuple, source.varargs, (source.annotations.get(source.varargs, Any), ...)
        )
        arg_generator = (
            (*argset, *star_argset)
            for argset, star_argset in zip(arg_generator, star_args_generator)
        )

    kwargs_generator: Iterator[dict[str, Any]] = generate_dicts_for_annotations(
        {k: source.annotations.get(k, Any) for k in source.kwonlyargs},
        context,
        optional_keys=[
            k for k in source.kwonlyargs if source.kwonlydefaults and k in source.kwonlydefaults
        ],
    )

    if source.varkw and context.generate_defaults:
        kw_type = source.annotations.get(source.varkw, Any)
        origin = typing.get_origin(kw_type)
        args = typing.get_args(kw_type)

        varkw_generator: Iterator[dict[str, Any]]
        if origin is None or origin is not typing.Unpack:
            varkw_generator = context.step(dict, source.varkw, (str, kw_type))
        else:
            varkw_generator = context.step((*args, Any)[0], source.varkw)

        if varkw_generator:
            kwargs_generator = (
                dict(**args, **{k: v for k, v in kwargs.items() if k not in args})
                for args, kwargs in zip(kwargs_generator, varkw_generator)
            )

    return zip(arg_generator, kwargs_generator)


def generate_enums(context: "AnnotationProcessingContext") -> Iterator[Any] | None:
    if context.concretely_implements(enum.Enum) or context.concretely_implements(enum.IntEnum):
        return gen.one_of(context.source)
    return None


def generate_literals(context: "AnnotationProcessingContext") -> Iterator[Any] | None:
    if context.origin is typing.Literal:
        return gen.one_of(context.args)
    return None


def generate_dataclass_instances(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    if dataclasses.is_dataclass(context.source):
        return (context.source(**d) for d in generate_dicts_for_dataclass_model(context))
    return None


def generate_dicts_from_typeddict(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    is_match = typing.is_typeddict(context.source)
    if not is_match:
        try:
            import typing_extensions

            is_match = typing_extensions.is_typeddict(context.source)
        except ImportError:
            pass

    if is_match:
        optional: list[str] = sorted(getattr(context.source, "__optional_keys__", frozenset()))
        hints = get_type_hints(context.source, include_extras=True)
        return generate_dicts_for_annotations(
            {k: v for k, v in hints.items()}, context, optional_keys=list(optional)
        )

    return None


def generate_dicts(context: AnnotationProcessingContext) -> Iterator[dict[Any, Any]] | None:
    if context.concretely_implemented_by(dict):
        key, value, *_ = (*context.args, str, str)
        key_generator = context.step(key, "[Key]")
        value_generator = context.step(value, "[Value]")
        return context.wrap_with_debug_context(
            dict((k, v) for k, v, _ in zip(key_generator, value_generator, range(length)))
            for length in (r.randint(0, 5 - context.recursive_depth) for r in gen)
        )

    return None


def generate_results_from_call(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    if inspect.isfunction(context.source):
        argspec = inspect.getfullargspec(context.source)
        return (
            context.source(*a, **k)
            for a, k in generate_call_args_for_argspec(FullArgSpec(*argspec), context)
        )

    return None


def generate_named_tuples(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    if context.concretely_implements(tuple) and hasattr(context.source, "_field_defaults"):
        keys: tuple[str, ...] = context.source._fields  # noqa
        defaults: dict[str, Any] = context.source._field_defaults
        hints = get_type_hints(context.source, include_extras=True)
        dicts = generate_dicts_for_annotations(
            {k: hints.get(k, Any) for k in keys}, context, optional_keys=list(defaults.keys())
        )
        return (context.source(**d) for d in dicts)
    return None


def generate_tuples(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    if context.concretely_implemented_by(tuple):
        has_ellipsis = not context.args or Ellipsis in context.args
        specified_parts = tuple(a for a in context.args if a is not Ellipsis)

        generators = [context.step(arg, str(f"[{i}]")) for i, arg in enumerate(specified_parts)]

        if generators:
            specified_generator = zip(*generators)
        else:
            specified_generator = itertools.repeat(())  # type: ignore

        if has_ellipsis:
            extension_type = [Any, *specified_parts][-1]
            unspecified_generator = context.step(list, "...", (extension_type,))
            return (
                (*specified, *unspecified)
                for specified, unspecified in zip(specified_generator, unspecified_generator)
            )
        else:
            return specified_generator
    return None


def generate_unions(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    if context.origin in (typing.Union, types.UnionType) and context.args:
        return gen.one_of(*(context.step(arg, f"|") for arg in context.args))
    return None


def generate_lists_sets_frozen_sets(context: AnnotationProcessingContext) -> Iterator[Any] | None:
    for constructor in (list, set, frozenset):
        if context.concretely_implemented_by(constructor):
            arg = next(iter(context.args), Any)
            generator = context.step(arg)
            return (
                constructor(
                    [i for i, _ in zip(generator, range(r.randint(0, 5 - context.recursive_depth)))]
                )
                for r in gen
            )
    return None


def generate_unexpected_annotation(
    context: AnnotationProcessingContext,
) -> typing.Iterator[Any] | None:
    # Assume that the first argument is the actual type to generate
    if context.origin is not None and context.args is not None:
        annotated_inner = next(iter(context.args), Any)
        return context.step(annotated_inner)
    return None


def generate_annotated(context: AnnotationProcessingContext) -> typing.Iterator[Any] | None:
    if context.origin is typing.Annotated:
        annotated_inner = [*context.args, Any][0]
        examples = (v for ex in context.args[1:] if isinstance(ex, Examples) for v in ex)
        if examples:
            return gen.one_of(*examples)

        return context.step(annotated_inner)
    return None


def _dataclass_has_default(field: dataclasses.Field) -> bool:
    return (
        field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING
    )


def generate_forward_refs(context: AnnotationProcessingContext) -> typing.Iterator | None:
    match = isinstance(context.source, typing.ForwardRef)
    if not match:
        try:
            import typing_extensions

            match = isinstance(context.source, typing_extensions.ForwardRef)
        except ImportError:
            pass
    if match:
        ref = typing.cast(typing.ForwardRef, context.source)
        if ref.__forward_arg__ not in context.globals:
            raise GenerationError(f"Could not resolve forward ref {ref.__forward_arg__}")

        def generate_for_forward_ref():
            t = ref._evaluate(context.globals, locals(), frozenset())
            for i in context.step(t, ref.__forward_arg__, recursive=True):
                yield i

        return generate_for_forward_ref()
    return None
