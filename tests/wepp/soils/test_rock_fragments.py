"""Conservation and domain checks for the explicitly mineral conversion."""
import pytest
from wepppy.wepp.soils.rock_fragments import rock_mass_to_volume_fraction, rock_volume_to_mass_fraction

pytestmark = pytest.mark.unit


def test_one_cubic_centimeter_mass_inventory():
    # 0.2 cm3 mineral fragments weigh0.53g;0.8 cm3 fine earth weighs1.04g.
    mass_fraction = rock_volume_to_mass_fraction(0.2, 1.3)
    assert mass_fraction == pytest.approx(0.53 / 1.57)
    assert rock_mass_to_volume_fraction(0.53 / 1.57, 1.3) == pytest.approx(0.2)
    assert rock_volume_to_mass_fraction(0.2, 2.65) == pytest.approx(0.2)
    assert rock_volume_to_mass_fraction(0.2, 1.3, 1.3) == pytest.approx(0.2)


@pytest.mark.parametrize('convert', [rock_volume_to_mass_fraction, rock_mass_to_volume_fraction])
@pytest.mark.parametrize('fraction', [0.0, 1.0])
def test_endpoints(convert, fraction):
    assert convert(fraction, 1.3) == fraction


@pytest.mark.parametrize('convert', [rock_volume_to_mass_fraction, rock_mass_to_volume_fraction])
@pytest.mark.parametrize('fraction,fine,rock', [(-0.1, 1.3, 2.65), (1.1, 1.3, 2.65), (float('nan'), 1.3, 2.65), (0.2, 0, 2.65), (0.2, 1.3, float('inf')), (0.2, 1.3, -1)])
def test_invalid_basis_fails(convert, fraction, fine, rock):
    with pytest.raises(ValueError):
        convert(fraction, fine, rock)
