import pytest

from wepppy.all_your_base.all_your_base import RGBA


def test_rgba_fields_are_instance_specific() -> None:
    color_a = RGBA(10, 20, 30, 40)
    color_b = RGBA(200, 210, 220, 230)

    assert (color_a.red, color_a.green, color_a.blue, color_a.alpha) == (10, 20, 30, 40)
    assert (color_b.red, color_b.green, color_b.blue, color_b.alpha) == (200, 210, 220, 230)
    assert color_a != color_b


def test_rgba_is_immutable() -> None:
    color = RGBA(1, 2, 3, 4)

    with pytest.raises(AttributeError):
        setattr(color, "red", 10)

    with pytest.raises(TypeError):
        color[0] = 10  # type: ignore[index]
