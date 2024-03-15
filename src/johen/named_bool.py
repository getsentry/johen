import dataclasses


@dataclasses.dataclass
class NamedBool:
    message: str
    result: bool

    def __bool__(self):
        return self.result

    def __str__(self):
        return self.message

    __repr__ = __str__
