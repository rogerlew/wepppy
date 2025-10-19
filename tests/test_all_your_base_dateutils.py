import datetime as dt

import pytest

from wepppy.all_your_base.dateutils import Julian, YearlessDate, parse_date, parse_datetime


class TestJulian:
    def test_construct_from_julian_day(self) -> None:
        julian = Julian(32)
        assert julian.julian == 32
        assert (julian.month, julian.day) == (2, 1)

    def test_construct_from_month_day(self) -> None:
        julian = Julian(3, 15)
        assert julian.julian == 74
        assert (julian.month, julian.day) == (3, 15)

    def test_construct_from_keywords_validates_consistency(self) -> None:
        julian = Julian(julian=60, month=3, day=1)
        assert julian.julian == 60
        assert (julian.month, julian.day) == (3, 1)

    def test_invalid_inputs_raise_value_error(self) -> None:
        with pytest.raises(ValueError):
            Julian(2, 30)
        with pytest.raises(ValueError):
            Julian(julian=60, month=2, day=28)


class TestParseHelpers:
    def test_parse_datetime_happy_path(self) -> None:
        timestamp = "[2021-07-15T14:30:45.123456] INFO some message"
        result = parse_datetime(timestamp)
        assert result == dt.datetime(2021, 7, 15, 14, 30, 45, 123456)

    def test_parse_datetime_rejects_missing_brackets(self) -> None:
        with pytest.raises(ValueError):
            parse_datetime("2021-07-15T14:30:45.123456 INFO")

    def test_parse_date_accepts_common_separators(self) -> None:
        expected = dt.datetime(2022, 12, 31)
        assert parse_date("2022-12-31") == expected
        assert parse_date("2022/12/31") == expected
        assert parse_date("2022.12.31") == expected

    def test_parse_date_passthrough(self) -> None:
        moment = dt.datetime(2020, 1, 1)
        assert parse_date(moment) is moment

    def test_parse_date_rejects_unknown_format(self) -> None:
        with pytest.raises(ValueError):
            parse_date("20220101")


class TestYearlessDate:
    def test_constructor_validates_bounds(self) -> None:
        date = YearlessDate(2, 14)
        assert (date.month, date.day) == (2, 14)

    def test_constructor_invalid_input(self) -> None:
        with pytest.raises(ValueError):
            YearlessDate(13, 1)
        with pytest.raises(ValueError):
            YearlessDate(2, 30)

    def test_from_string_accepts_variants(self) -> None:
        result = YearlessDate.from_string("02/05")
        assert (result.month, result.day) == (2, 5)
        result = YearlessDate.from_string("YearlessDate(3, 1)")
        assert (result.month, result.day) == (3, 1)

    def test_from_string_rejects_bad_input(self) -> None:
        with pytest.raises(ValueError):
            YearlessDate.from_string("not-a-date")

    def test_yesterday_rolls_back_across_boundaries(self) -> None:
        prev = YearlessDate(3, 1).yesterday
        assert (prev.month, prev.day) == (2, 28)
        prev = YearlessDate(1, 1).yesterday
        assert (prev.month, prev.day) == (12, 31)

    def test_julian_property_matches_month_day(self) -> None:
        assert YearlessDate(2, 1).julian == 32
