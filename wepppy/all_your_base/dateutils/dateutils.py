
from datetime import datetime, timedelta, date


class Julian(object):
    def __init__(self, *args, **kwargs):

        # noinspection PyUnusedLocal
        __slots__ = ["julian", "month", "day"]

        if len(kwargs) > 0:
            assert "julian" in kwargs
            julian = kwargs['julian']
            assert julian > 0
            assert julian <= 365

            assert "month" in kwargs
            assert "day" in kwargs
            month = kwargs['month']
            day = kwargs['day']

            _m, _d = _julian_to_md(julian)
            assert _m == month
            assert _d == day

            super(Julian, self).__setattr__("julian", julian)
            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

        if len(args) == 1:
            julian = int(args[0])
            assert julian >= 0
            assert julian <= 365

            super(Julian, self).__setattr__("julian", julian)

            month, day = _julian_to_md(julian)
            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

        elif len(args) == 2:
            month = int(args[0])
            day = int(args[1])
            assert month > 0
            assert month <= 12

            assert day > 0
            assert day <= _days[month-1]

            super(Julian, self).__setattr__("month", month)
            super(Julian, self).__setattr__("day", day)

            julian = _md_to_julian(month, day)
            super(Julian, self).__setattr__("julian", julian)

    def __str__(self):
        # noinspection PyUnresolvedReferences
        return str(self.julian)

    def __repr__(self):
        # noinspection PyUnresolvedReferences
        return 'Julian(julian=%i, month=%i, day=%i)'\
               % (self.julian, self.month, self.day)


def parse_datetime(s):
    return datetime.strptime(s[1:s.find(']')], '%Y-%m-%dT%H:%M:%S.%f')


def parse_date(x):
    if isinstance(x, datetime):
        return x

    ymd = x.split('-')
    if len(ymd) != 3:
        ymd = x.split('/')
    if len(ymd) != 3:
        ymd = x.split('.')

    y, m, d = ymd
    y = int(y)
    m = int(m)
    d = int(d)

    return datetime(y, m, d)


_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_cummdays = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]


def _julian_to_md(julian):
    for i, (d, cd) in enumerate(zip(_days, _cummdays)):
        if julian <= cd:
            return i+1, d - (cd - julian)


def _md_to_julian(month, day):
    return _cummdays[month-1] + day - _days[month-1]


class YearlessDate(object):
    def __init__(self, month, day):
        month = int(month)
        day = int(day)
        assert month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.month = month

        assert day > 0
        assert day <= _days[month-1]
        self.day = day

    @staticmethod
    def from_string(s):
        if s.startswith('YearlessDate('):
            s = s[13:-1].replace(',', '-').replace(' ', '')

        for delimiter in '/ -.':
            _s = s.split(delimiter)
            if len(_s) == 2:
                month, day = _s
                return YearlessDate(month, day)

        raise Exception

    @property
    def yesterday(self):
        d = date(2001, self.month, self.day) - timedelta(1)
        return YearlessDate(d.month, d.day)

    @property
    def julian(self):
        return _md_to_julian(self.month, self.day)
    
    def __str__(self):
        return '{0.month}/{0.day}'.format(self)

    def __repr__(self):
        return 'YearlessDate({0.month}, {0.day})'.format(self)
