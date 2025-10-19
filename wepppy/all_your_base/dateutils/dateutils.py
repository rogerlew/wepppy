"""Calendar helpers for translating between Julian and month/day representations."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Tuple

__all__ = [
    'Julian',
    'YearlessDate',
    'parse_datetime',
    'parse_date',
]


_days: Tuple[int, ...] = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_cummdays: Tuple[int, ...] = (31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365)


class Julian:
    """Representation of a Julian day alongside its calendar month and day."""

    __slots__ = ('julian', 'month', 'day')

    julian: int
    month: int
    day: int

    def __init__(self, *args: int, **kwargs: int) -> None:
        """Construct either from a Julian day or from a month/day pair."""
        if kwargs:
            self._init_from_kwargs(kwargs)
            return

        if len(args) == 1:
            self._init_from_julian(args[0])
        elif len(args) == 2:
            self._init_from_month_day(args[0], args[1])
        else:
            raise ValueError('Julian requires either a julian day or month/day pair.')

    def _init_from_kwargs(self, kwargs: dict[str, int]) -> None:
        if {'julian', 'month', 'day'} - set(kwargs):
            raise ValueError('julian, month, and day keyword arguments are required.')
        self._init_from_julian(kwargs['julian'])
        if self.month != kwargs['month'] or self.day != kwargs['day']:
            raise ValueError('Julian day does not match provided month/day.')

    def _init_from_julian(self, julian: int) -> None:
        julian = int(julian)
        if not 0 <= julian <= 365:
            raise ValueError('Julian day must be within [0, 365].')
        object.__setattr__(self, 'julian', julian)
        month, day = _julian_to_md(julian)
        object.__setattr__(self, 'month', month)
        object.__setattr__(self, 'day', day)

    def _init_from_month_day(self, month: int, day: int) -> None:
        month = int(month)
        day = int(day)
        if not 1 <= month <= 12:
            raise ValueError('Month must be in the range [1, 12].')
        if not 1 <= day <= _days[month - 1]:
            raise ValueError('Invalid day for the specified month.')
        object.__setattr__(self, 'month', month)
        object.__setattr__(self, 'day', day)
        julian = _md_to_julian(month, day)
        object.__setattr__(self, 'julian', julian)

    def __str__(self) -> str:
        return str(self.julian)

    def __repr__(self) -> str:
        return f'Julian(julian={self.julian}, month={self.month}, day={self.day})'


def parse_datetime(value: str) -> datetime:
    """Parse a WEPP log string timestamp into a :class:`datetime`."""
    start = value.find('[')
    end = value.find(']')
    if start == -1 or end == -1 or end <= start + 1:
        raise ValueError(f'Cannot parse datetime from {value!r}.')
    return datetime.strptime(value[start + 1:end], '%Y-%m-%dT%H:%M:%S.%f')


def parse_date(value: str | datetime) -> datetime:
    """Return a :class:`datetime` from common string representations."""
    if isinstance(value, datetime):
        return value

    for separator in ('-', '/', '.'):
        components = value.split(separator)
        if len(components) == 3:
            break
    else:
        raise ValueError(f'Unrecognized date format: {value}')

    year, month, day = (int(part) for part in components)
    return datetime(year, month, day)


def _julian_to_md(julian: int) -> tuple[int, int]:
    for index, (days, cumulative) in enumerate(zip(_days, _cummdays)):
        if julian <= cumulative:
            return index + 1, days - (cumulative - julian)
    raise ValueError('Julian day must be within [0, 365].')


def _md_to_julian(month: int, day: int) -> int:
    return _cummdays[month - 1] + day - _days[month - 1]


class YearlessDate:
    """Month/day pair without a fixed year."""

    __slots__ = ('month', 'day')

    month: int
    day: int

    def __init__(self, month: int, day: int) -> None:
        month = int(month)
        day = int(day)
        if month not in range(1, 13):
            raise ValueError('Month must be between 1 and 12.')
        if not 1 <= day <= _days[month - 1]:
            raise ValueError('Invalid day for the specified month.')
        self.month = month
        self.day = day

    @staticmethod
    def from_string(value: str) -> 'YearlessDate':
        """Create a :class:`YearlessDate` from typical ``MM/DD``-style strings."""
        if value.startswith('YearlessDate('):
            value = value[13:-1].replace(',', '-').replace(' ', '')

        for delimiter in '/ -.':
            parts = value.split(delimiter)
            if len(parts) == 2:
                return YearlessDate(int(parts[0]), int(parts[1]))

        raise ValueError(f'Could not parse YearlessDate from {value!r}.')

    @property
    def yesterday(self) -> 'YearlessDate':
        reference = date(2001, self.month, self.day) - timedelta(days=1)
        return YearlessDate(reference.month, reference.day)

    @property
    def julian(self) -> int:
        return _md_to_julian(self.month, self.day)

    def __str__(self) -> str:
        return f'{self.month}/{self.day}'

    def __repr__(self) -> str:
        return f'YearlessDate({self.month}, {self.day})'
