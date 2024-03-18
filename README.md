# johen
Generative (property) testing, from python annotations.

Inspired by QuickCheck, similar goals to [hypothesis](https://hypothesis.readthedocs.io/en/latest/), but focused on
annotations doing the heavy lifting.

## Quick Usage

Enable the plugin in your pytest configuration, then 
use `@parametrize` on a test function and get things.

```python
from johen.pytest import parametrize

@parametrize
def test_thing(my_model: Model, inputs: list[str]):
  my_model.update(a=inputs)
  assert my_model.a == inputs
```

Works on many common types of datatypes:
* Named tuples
* dataclasses
* pydantic v2 models (opt in)
* sqlalchemy models (opt in)
* tuples, lists, sets
* TypedDict
* primitives
* UUIDs
* easy to extend to support more types

## Configuration

Use `parametrize` to configure options for specific test groups.
For instance, you can use `arg_set` to distinguish generated arguments vs fixtures.

```python
@parametrize(count=15, seed=2, arg_set=('a',))
def my_test(a: int, unrelated_fixture):
  pass
```

Use `replace_global_config` to conditionally update global options, or write
directly to `global_config` if you intend to persist your config adjustments.

```python
global_config.matches.append(my_custom_matcher)

@pytest.fixture(autouse=True)
def setup_config():
    with replace_global_config(dict(max_iterations=500)):
        yield
```

## Add new generation types

You have two main strategies.  

The easiest is to add the type to `"type_matchers"` of the global_config.
You can use python generator expressions in combination with `gen` to create deterministic generative methods.

```python
from johen import global_config, gen

global_config["type_matchers"][MyType] = (MyType(r.randint(0, 10)) for r in gen)
```

The other is to add a custom `AnnotationMatcher` to the `"matchers"` key.  See generates/base.py for examples.

## Recursive Types

It is possible to support recursive types through forward references, but do note that
their generation is typically expensive.  Use the `"globals"` key of the `global_config`
to configure the forward refs ahead of time:

```python
from johen.specialized import JsonDict, JsonValue

global_config['globals'].extend({
  "JsonDict": JsonDict,
  "JsonValue": JsonValue,
})
```