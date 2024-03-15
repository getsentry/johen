from typing import Any, Iterator, get_type_hints

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from johen.generators.annotations import AnnotationProcessingContext
from johen.generators.base import generate_dicts_for_annotations


def generate_dicts_for_pydantic_model(
    context: "AnnotationProcessingContext",
) -> Iterator[dict[str, Any]]:
    hints = get_type_hints(context.source, include_extras=True)
    return generate_dicts_for_annotations(
        {k: hints.get(k, Any) for k, field in context.source.model_fields.items()},
        context,
        optional_keys=[
            k for k, field in context.source.model_fields.items() if _pydantic_has_default(field)
        ],
    )


def generate_pydantic_instances(context: AnnotationProcessingContext) -> Iterator[BaseModel] | None:
    if isinstance(context.source, type) and issubclass(context.source, BaseModel):
        return (context.source(**d) for d in generate_dicts_for_pydantic_model(context))
    return None


def _pydantic_has_default(field: FieldInfo) -> bool:
    return field.default is not PydanticUndefined or field.default_factory is not None
