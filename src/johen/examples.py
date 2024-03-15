from typing import Any, Iterable


class Examples:
    """
    Annotate types with this item in order to get example inputs as part of test generation.
    """

    def __init__(self, *args: Iterable[Any]):
        self.args = args

    def __iter__(self):
        return iter(self.args)

    def __str__(self):
        return f"Examples({self.args!r})"

    __repr__ = __str__
