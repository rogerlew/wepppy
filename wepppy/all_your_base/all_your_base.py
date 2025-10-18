# Copyright (c) 2016-2020, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Miscellaneous utilities shared across the all_your_base package."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any, NamedTuple, Optional, TypeAlias, Union

import os
from os.path import exists as _exists
from operator import itemgetter
from itertools import groupby
import shutil
import math
import random
import multiprocessing

import json
import numpy as np

try:
    NCPU: int = int(os.environ['WEPPPY_NCPU'])
except KeyError:
    NCPU = math.floor(multiprocessing.cpu_count() * 0.5)
    if NCPU < 1:
        NCPU = 1

geodata_dir: str = '/geodata/'
SCRATCH: str = '/media/ramdisk'

if not _exists(SCRATCH):
    SCRATCH = '/Users/roger/Downloads'

if not _exists(SCRATCH):
    SCRATCH = '/workdir/scratch'

IS_WINDOWS: bool = os.name == 'nt'

__all__ = [
    'NCPU',
    'geodata_dir',
    'SCRATCH',
    'IS_WINDOWS',
    'RGBA',
    'NumpyEncoder',
    'cmyk_to_rgb',
    'flatten',
    'find_ranges',
    'clamp',
    'clamp01',
    'cp_chmod',
    'splitall',
    'isint',
    'isfloat',
    'isbool',
    'isnan',
    'isinf',
    'try_parse',
    'try_parse_float',
    'parse_name',
    'parse_units',
    'RowData',
    'c_to_f',
    'f_to_c',
]


class RGBA(NamedTuple):
    """Simple representation of a colour with alpha channel."""

    red: int
    green: int
    blue: int
    alpha: int = 255

    def tohex(self) -> str:
        """Return the color encoded as ``#RRGGBBAA``."""
        return '#' + ''.join(f'{component:02X}' for component in self)

    @classmethod
    def random(cls) -> RGBA:
        """Generate a random opaque RGBA color."""
        return cls(
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
            255,
        )


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that serializes numpy scalars and arrays."""

    def default(self, obj: Any) -> Any:
        """Return a JSON-serializable representation of ``obj``."""
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def cmyk_to_rgb(c: float, m: float, y: float, k: float) -> tuple[float, float, float]:
    """Convert CMYK color components into their RGB equivalents.

    Args:
        c: Cyan component in the range ``[0.0, 1.0]``.
        m: Magenta component in the range ``[0.0, 1.0]``.
        y: Yellow component in the range ``[0.0, 1.0]``.
        k: Key (black) component in the range ``[0.0, 1.0]``.

    Returns:
        Normalized red, green, and blue components.
    """
    r = (1.0 - c) * (1.0 - k)
    g = (1.0 - m) * (1.0 - k)
    b = (1.0 - y) * (1.0 - k)
    return r, g, b


def flatten(iterable: Iterable[Any]) -> Iterator[Any]:
    """Yield each scalar item from ``iterable``, flattening nested iterables.

    Args:
        iterable: Arbitrarily nested iterable containing scalar values.

    Yields:
        Each scalar element in depth-first order.
    """
    for item in iterable:
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            yield from flatten(item)
        else:
            yield item


RangeType: TypeAlias = Union[int, tuple[int, int]]


def find_ranges(iterable: Iterable[int], as_str: bool = False) -> Union[list[RangeType], str]:
    """Collapse consecutive integers into ranges.

    Args:
        iterable: A sorted collection of integers.
        as_str: When True, return a comma-separated string representation.

    Returns:
        Either a list describing each range, or a formatted string when ``as_str`` is True.
    """

    def func(args: tuple[int, int]) -> int:
        index, item = args
        return index - item

    ranges: list[RangeType] = []
    for key, group in groupby(enumerate(iterable), func):
        group = list(map(itemgetter(1), group))
        if len(group) > 1:
            ranges.append((group[0], group[-1]))
        else:
            ranges.append(group[0])

    if not as_str:
        return ranges

    s = []

    for arg in ranges:
        if isint(arg):
            s.append(str(arg))
        else:
            s.append('{}-{}'.format(*arg))
    return ', '.join(s)


def clamp(x: float, minimum: float, maximum: float) -> float:
    """Clamp ``x`` to the inclusive range defined by ``minimum`` and ``maximum``.

    Args:
        x: Value to clamp.
        minimum: Lower bound of the permitted range.
        maximum: Upper bound of the permitted range.

    Returns:
        The clamped float.
    """
    x = float(x)
    if x < minimum:
        return minimum
    elif x > maximum:
        return maximum
    return x


def clamp01(x: float) -> float:
    """Clamp ``x`` between ``0.0`` and ``1.0``.

    Args:
        x: Value to clamp.

    Returns:
        The clamped float.
    """
    x = float(x)
    if x < 0.0:
        return 0.0
    elif x > 1.0:
        return 1.0
    return x


def cp_chmod(src: str, dst: str, mode: int) -> None:
    """Copy ``src`` to ``dst`` and apply the requested file mode.

    Args:
        src: Source path.
        dst: Destination path.
        mode: Permission bits passed to :func:`os.chmod`.
    """
    shutil.copyfile(src, dst)
    os.chmod(dst, mode)


def splitall(path: str) -> list[str]:
    """Split a file system path into all of its components.

    Args:
        path: Path to split.

    Returns:
        A list of path components including the root.
    """
    allparts: list[str] = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:   # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def isint(x: Any) -> bool:
    """Return whether ``x`` can be losslessly converted to an integer.

    Args:
        x: Value to inspect.

    Returns:
        True when ``x`` coerces to an integer without changing magnitude.
    """
    # noinspection PyBroadException
    try:
        return float(int(x)) == float(x)
    except Exception:
        return False


def isfloat(f: Any) -> bool:
    """Return whether ``f`` can be converted to a float.

    Args:
        f: Value to inspect.

    Returns:
        True when ``f`` coerces to :class:`float`.
    """
    # noinspection PyBroadException
    try:
        float(f)
        return True
    except Exception:
        return False


def isbool(x: Any) -> bool:
    """Return whether ``x`` behaves like a boolean value.

    Args:
        x: Value to inspect.

    Returns:
        True when ``x`` is 0/1 or an explicit boolean.
    """
    # noinspection PyBroadException
    return x in (0, 1, True, False)


def isnan(f: Any) -> bool:
    """Return whether ``f`` is a NaN value.

    Args:
        f: Value to inspect.

    Returns:
        True when ``f`` represents ``math.nan``.
    """
    if not isfloat(f):
        return False
    return math.isnan(float(f))


def isinf(f: Any) -> bool:
    """Return whether ``f`` represents positive or negative infinity.

    Args:
        f: Value to inspect.

    Returns:
        True when ``f`` represents positive or negative infinity.
    """
    if not isfloat(f):
        return False
    return math.isinf(float(f))


def try_parse(f: Any) -> Any:
    """Best-effort conversion of ``f`` to int or float.

    Args:
        f: Value to attempt to coerce.

    Returns:
        A numeric conversion of ``f`` when possible, otherwise ``f`` unchanged.
    """
    if isinstance(f, (int, float)):
        return f

    # noinspection PyBroadException
    try:
        ff = float(f)
        # noinspection PyBroadException
        try:
            fi = int(f)
            return fi
        except Exception:
            return ff
    except Exception:
        return f


def try_parse_float(f: Any, default: float = 0.0) -> float:
    """Attempt to convert ``f`` to a float.

    Args:
        f: Value to attempt to convert.
        default: Value returned when conversion fails.

    Returns:
        The converted float value or ``default``.
    """
    # noinspection PyBroadException
    try:
        return float(f)
    except Exception:
        return default


def parse_name(colname: str) -> str:
    """Return the column name without any trailing unit specification.

    Args:
        colname: Column label that may contain unit metadata.

    Returns:
        The column label stripped of ``(<units>)`` suffixes.
    """
    units = parse_units(colname)
    if units is None:
        return colname

    return colname.replace('({})'.format(units), '').strip()


def parse_units(colname: str) -> Optional[str]:
    """Extract unit metadata from ``colname`` if present.

    Args:
        colname: Column label that may contain a unit suffix.

    Returns:
        The unit string or ``None`` when no units are detected.
    """
    try:
        colsplit = colname.strip().split()
        if len(colsplit) < 2:
            return None

        if '(' in colsplit[-1]:
            return colsplit[-1].replace('(', '').replace(')', '')

        return None
    except IndexError:
        return None


class RowData:
    """Helper wrapper that exposes dict-like row objects with unit parsing.

    Args:
        row: Mapping of column headings to values.
    """

    def __init__(self, row: Mapping[str, Any]) -> None:
        self.row = row

    def __getitem__(self, item: str) -> Any:
        """Return the value for the first column that starts with ``item``.

        Args:
            item: Column prefix to match.

        Returns:
            The column value whose heading begins with ``item``.

        Raises:
            KeyError: When no column heading matches the prefix.
        """
        for colname in self.row:
            if colname.startswith(item):
                return self.row[colname]

        raise KeyError

    def __iter__(self) -> Iterator[tuple[Any, Optional[str]]]:
        """Iterate over column values paired with their parsed units.

        Yields:
            Two-tuples of ``(value, units)``.
        """
        for colname in self.row:
            value = self.row[colname]
            units = parse_units(colname)
            yield value, units


def c_to_f(x: float) -> float:
    """Convert Celsius to Fahrenheit.

    Args:
        x: Temperature in degrees Celsius.

    Returns:
        The corresponding Fahrenheit value.
    """
    return 9.0/5.0 * x + 32.0


def f_to_c(x: float) -> float:
    """Convert Fahrenheit to Celsius.

    Args:
        x: Temperature in degrees Fahrenheit.

    Returns:
        The corresponding Celsius value.
    """
    return (x - 32.0) * 5.0 / 9.0
