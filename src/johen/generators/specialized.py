import datetime
import hashlib
import itertools
import math
import string
import struct
import uuid

try:
    from typing_extensions import TypeAlias
except ImportError:
    from typing import TypeAlias

from typing import Annotated, Dict, List, Union

from johen.examples import Examples
from johen.random import gen

simple_symbol = ("".join(r.sample(string.ascii_letters + "_", 5)) for r in gen)
unsigned_ints = (r.getrandbits(2 ** r.randint(0, 6)) for r in gen)
negative_ints = (i * -1 for i in unsigned_ints)
ints = gen.one_of(unsigned_ints, negative_ints, (0,))
bit_packed_floats = (struct.unpack("d", struct.pack("Q", bits))[0] for bits in unsigned_ints)
valid_floats = (v for v in bit_packed_floats if not math.isinf(v) and not math.isnan(v))
invalid_floats = gen.one_of((math.inf, math.nan))
all_floats = gen.one_of(valid_floats, invalid_floats)
bools = gen.one_of([True, False])
objects = (object() for _ in gen)
printable_strings = ("".join(r.sample(string.printable, r.randint(0, 6))) for r in gen)
colors = gen.one_of(
    [
        "red",
        "green",
        "blue",
        "orange",
        "purple",
        "cyan",
        "magenta",
        "magenta",
        "yellow",
        "gold",
        "silver",
        "black",
        "white",
    ]
)
things = gen.one_of(
    [
        "shirt",
        "sneaker",
        "shoe",
        "apple",
        "banana",
        "orange",
        "tea",
        "sandwich",
        "tennis",
        "football",
        "basketball",
        "fork",
        "table",
        "computer",
    ]
)
names = gen.one_of(
    [
        "bob",
        "alice",
        "jennifer",
        "john",
        "mary",
        "jane",
        "sally",
        "fred",
        "dan",
        "alex",
        "margaret",
        "vincent",
        "timothy",
        "samuel",
    ]
)
ascii_words = ("-".join(group) for group in zip(colors, names, things))
dates = (
    datetime.date(2013, 1, 1)
    + datetime.timedelta(
        days=r.randint(0, 365 * 20),
    )
    for r in gen
)
datetimes = (
    datetime.datetime(2013, 1, 1, 1)
    + datetime.timedelta(
        days=r.randint(0, 365 * 20),
        seconds=r.randint(0, 60 * 60 * 24),
        milliseconds=r.randint(0, 1000),
    )
    for r in gen
)
positive_timedeltas = (
    datetime.timedelta(seconds=r.randint(0, 59), hours=r.randint(0, 23)) for r in gen
)
uuids = (uuid.UUID(int=r.getrandbits(128), version=4) for r in gen)
uuid_hexes = (uid.hex for uid in uuids)
file_extensions = gen.one_of(
    (".jpg", ".png", ".gif", ".txt", ".py", ".ts", ".c", ".obj", ".ini", "")
)
path_segments = gen.one_of(
    (
        ".",
        "..",
        "tmp",
        "var",
        "usr",
        "Home",
        "data",
        "volumes",
        "etc",
        "tests",
        "src",
        "db",
        "conf",
        "events",
        "utils",
        "app",
        "versions",
        "models",
    ),
    uuid_hexes,
)
file_paths = (
    lead + "/".join(segment for _, segment in segments) + ext
    for lead, segments, ext in zip(
        gen.one_of(("", "/")),
        (zip(range(r.randint(1, 8)), path_segments) for r in gen),
        file_extensions,
    )
)
file_names = (segment + ext for segment, ext in zip(path_segments, file_extensions))
byte_strings = (s.encode("utf8") for s in printable_strings)
sha1s = (hashlib.sha1(s).hexdigest() for s in byte_strings)
json_primitives = gen.one_of(ascii_words, ints, bools, valid_floats, itertools.repeat(None))
nones = itertools.repeat(None)


UnsignedInt = Annotated[int, Examples(unsigned_ints)]
NegativeInt = Annotated[int, Examples(negative_ints)]
ValidFloat = Annotated[float, Examples(valid_floats)]
InvalidFloat = Annotated[float, Examples(invalid_floats)]
ValidOrInvalidFloat = Annotated[bool, Examples(all_floats)]
AsciiWord = Annotated[str, Examples(ascii_words)]
FileName = Annotated[str, Examples(file_names)]
FilePath = Annotated[str, Examples(file_paths)]
Sha1 = Annotated[str, Examples(sha1s)]
SimpleSymbol = Annotated[str, Examples(simple_symbol)]


JsonValue: TypeAlias = Union[int, float, str, bool, None, List["JsonValue"], "JsonDict"]
JsonDict: TypeAlias = Dict[str, JsonValue]
