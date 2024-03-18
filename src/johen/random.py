import dataclasses
import random
import typing
from typing import Iterator

_A = typing.TypeVar("_A")


__all__ = ["gen"]


@dataclasses.dataclass
class _RandomGenerator:
    """
    A global, nearly-never ending generator for producing Random instances to other random source generators.
    Allows its generation to be seeded, ensuring that consumers of this iterator will behave deterministically
    given that they draw all their source of random variables from this iterator.

    Use the `gen` variable directly to construct such sources of generative data:
    my_integers = (r.randint(0, 100) for r in gen)
    """

    last_seed: int = 0
    r: random.Random = dataclasses.field(default_factory=lambda: random.Random(0))
    # A control valve that breaks the halting problem in the case of a bug, or at least highly costly generative step.
    remaining_iterations: int = (
        -1
    )  # Reset this before generating each parameter at the top of a process.

    def restart_at(self, seed: int):
        self.last_seed = seed
        self.r = random.Random(seed)

    def wrap_deterministically(
        self, iter: Iterator[_A], seed: int, max_iterations: int
    ) -> Iterator[_A]:
        """
        Enforces deterministic seed resolution, and a max_iterations per top level yield.
        """

        def wrapped():
            self.restart_at(seed)
            self.remaining_iterations = max_iterations
            for rv in iter:
                yield rv
                self.restart_at_next_seed()
                self.remaining_iterations = max_iterations

        return wrapped()

    def restart_at_next_seed(self):
        self.restart_at(self.last_seed)
        next_seed = self.r.getrandbits(64)
        self.restart_at(next_seed)
        return self

    def __next__(self) -> "random.Random":
        if self.remaining_iterations <= 0:
            raise StopIteration("Could not find generation")
        self.remaining_iterations -= 1
        return self.r

    def __iter__(self) -> "Iterator[random.Random]":
        return self

    @staticmethod
    def one_of(*options: typing.Iterable[_A]) -> Iterator[_A]:
        composed_options: list[typing.Iterable[_A]] = [
            _RandomGenerator._normalize(i) for i in options
        ]
        return (next(iter(r.choice(composed_options))) for r in gen)

    @staticmethod
    def _normalize(i: typing.Iterable[_A]) -> typing.Iterator[_A]:
        if not hasattr(i, "__next__"):
            i = list(i)
            return (r.choice(i) for r in gen)
        return iter(i)


gen = _RandomGenerator()
