import inspect
import typing
from typing import Any, get_type_hints

import sqlalchemy.orm

from johen.generators.annotations import AnnotationProcessingContext
from johen.generators.base import generate_dicts_for_annotations


def generate_sqlalchemy_instance(
    context: AnnotationProcessingContext,
) -> typing.Iterator[Any] | None:
    import sqlalchemy.orm

    if inspect.isclass(context.source) and issubclass(
        context.source, sqlalchemy.orm.DeclarativeBase
    ):
        hints = get_type_hints(context.source, include_extras=True)
        inspection = sqlalchemy.inspect(context.source)
        dict_generator = generate_dicts_for_annotations(
            {
                c.key: next(iter(typing.get_args(hint)), Any)  # type: ignore
                if typing.get_origin(hint) is sqlalchemy.orm.Mapped
                else hint
                for c in inspection.c
                for hint in (hints.get(c.key, Any),)
            },
            context,
            optional_keys=[
                c.key
                for c in inspection.c
                if (
                    c.primary_key
                    or c.nullable
                    or c.default is not None
                    or c.server_default is not None
                )
            ],
        )

        return (context.source(**d) for d in dict_generator)
    return None
