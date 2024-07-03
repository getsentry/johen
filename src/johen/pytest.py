import dataclasses
import functools
import inspect
import typing
from collections import defaultdict
from typing import Any

import pytest

from johen.config import ParametrizeConfig, compile_matchers, pick_seed_from_name, updated_config
from johen.exc import GenerationError
from johen.generators.annotations import AnnotationProcessingContext
from johen.generators.base import generate_dicts_for_annotations
from johen.globals import global_config
from johen.random import gen

_C = typing.TypeVar("_C", bound=typing.Callable)

try:
    from typing_extensions import Unpack
except ImportError:
    from typing import Unpack


@dataclasses.dataclass
class _parametrize:
    config: list[ParametrizeConfig] = dataclasses.field(default_factory=lambda: [global_config])

    @typing.overload
    def __call__(self, test: _C, **kwargs: Unpack[ParametrizeConfig]) -> "_C":
        pass

    @typing.overload
    def __call__(self, test: None = None, **kwargs: Unpack[ParametrizeConfig]) -> "_parametrize":
        pass

    def __call__(
        self, test: _C | None = None, **kwargs: Unpack[ParametrizeConfig]
    ) -> "_parametrize | _C":
        if kwargs:
            p = _parametrize([*self.config, kwargs])
        else:
            p = self

        if test is None:
            return p

        configs = p.config
        gather_config: ParametrizeConfig = functools.reduce(updated_config, configs)
        argspec = inspect.getfullargspec(test)
        injected_args = sorted(
            gather_config["arg_set"] if gather_config["arg_set"] is not None else argspec.args
        )

        if not injected_args:
            return test

        if gather_config["seed"] is None:
            final_seed = pick_seed_from_name(test.__name__)
        else:
            final_seed = gather_config["seed"]

        count = gather_config["count"]
        assert count > 0, "count must be greater than 0"

        @functools.cache
        def get_call_args() -> typing.Iterator[dict]:
            final_config: ParametrizeConfig = functools.reduce(
                updated_config, [global_config, *configs[1:]]
            )

            if invalid_arg := next(
                (k not in injected_args for k in final_config["overrides"].keys()), None
            ):
                raise ValueError(
                    f"Argument {invalid_arg} cannot be overriden, check your arg_set and overrides arguments to parametrize."
                )

            context = AnnotationProcessingContext.from_source(test)
            context.generate_defaults = final_config["generate_defaults"]
            context.matchers = compile_matchers(final_config)
            context.globals = final_config["globals"]
            return gen.wrap_deterministically(
                generate_dicts_for_annotations(
                    {
                        k: final_config["overrides"].get(k, argspec.annotations.get(k, Any))
                        for k in injected_args
                    },
                    context,
                    optional_keys=[],
                ),
                seed=final_seed,
                max_iterations=final_config["max_iterations"],
            )

        cached: list[dict[str, Any]] = []

        def _get_arg_slice(arg: str) -> typing.Callable[[int], typing.Callable[[], Any]]:
            def _get_arg_thunk(index: int):
                def _thunk():
                    call_args = get_call_args()
                    while len(cached) < count:
                        try:
                            cached.append(next(call_args))
                        except StopIteration as e:
                            raise GenerationError(
                                f"Failed to generate {count} test cases for {test.__name__}, check that constraint is not too strong."
                            ) from e
                    return cached[index][arg]

                _thunk.__name__ = f"{arg}-{index}"
                return _thunk

            return _get_arg_thunk

        return pytest.mark.johen(count, injected_args)(
            pytest.mark.parametrize(
                injected_args,
                [
                    [_get_arg_slice(k)(i) for k in injected_args]
                    for i in range(gather_config["count"])
                ],
                indirect=(),
            )(test)
        )


def pytest_configure(config: pytest.Config):
    config.addinivalue_line(
        "markers", "johen(injected): marks a test for parametrization via the johen.pytest hooks."
    )


_default = object()


@dataclasses.dataclass
class Sometimes:
    calls: dict[tuple[str, int], tuple[set[int], set[int]]] = dataclasses.field(
        default_factory=lambda: defaultdict(lambda: (set(), set()))
    )

    def __call__(self, cond: Any) -> bool:
        result = bool(cond)
        frameinfo = inspect.getouterframes(inspect.currentframe())[1]

        hits, misses = self.calls[(frameinfo.filename, frameinfo.lineno)]

        if not result:
            misses.add(gen.last_seed)
            return True

        hits.add(gen.last_seed)
        return True


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item: pytest.Item):
    if not isinstance(item, pytest.Function):
        yield
        return

    mark = item.get_closest_marker("johen")
    if mark is None:
        # In this case, at the very least, reset the seed deterministically for raw `generate` calls.
        gen.restart_at(pick_seed_from_name(item.name))
        yield
        return

    injected: list[str] = mark.args[1]

    if hasattr(item, "callspec"):
        for k in injected:
            # apply the thunk.
            item.callspec.params[k] = item.callspec.params[k]()  # type: ignore
    else:
        raise GenerationError(
            f"Test {item.name!r} does not support parametrization, you will need to invoke `generate` directly."
        )

    yield


sometimes = Sometimes()


_runs_remaining = 0
_last_item = -1


@pytest.fixture(autouse=True)
def check_sometimes_misses(request: pytest.FixtureRequest):
    global _last_item, _runs_remaining

    node = request.node
    marker = node.get_closest_marker("johen")
    if not isinstance(node, pytest.Function) or not marker:
        yield
        return

    fid = id(node.obj)

    if fid != _last_item:
        _last_item = fid
        _runs_remaining = marker.args[0]
        sometimes.calls.clear()

    yield

    _runs_remaining -= 1
    if _runs_remaining > 0:
        return

    failure_lines = []
    for (filename, lineno), (hits, misses) in sometimes.calls.items():
        if len(hits) == marker.args[0]:
            failure_lines.append(
                f"{filename}:{lineno} -- all tests hit, try increasing count to find counterfactuals"
            )
        elif not hits:
            failure_lines.append(f"{filename}:{lineno} -- no hits, try different seed or count")
    if failure_lines:
        assert False, "sometimes failures\n" + "\n".join(failure_lines)


parametrize = _parametrize()
