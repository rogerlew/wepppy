"""Mass/volume conversions for mineral coarse fragments, never surface cover.

Densities are in g/cm3. Fine-earth density includes fine-earth pores; fragment
volume is its envelope volume. The 2.65 mineral convention matches native WEPP.
See docs/schemas/rock-fragment-representation-contract.md for physical limits.
"""
from math import isfinite

__all__ = ['rock_volume_to_mass_fraction', 'rock_mass_to_volume_fraction']


def _validate(fraction: float, fine_earth_density: float, rock_density: float) -> None:
    if not isfinite(fraction) or not 0.0 <= fraction <= 1.0:
        raise ValueError('Rock fraction must be finite and between 0 and 1')
    if not all(isfinite(value) and value > 0 for value in (fine_earth_density, rock_density)):
        raise ValueError('Fine-earth and rock densities must be finite and positive')


def rock_volume_to_mass_fraction(
    volume_fraction: float, fine_earth_density: float, rock_density: float = 2.65,
) -> float:
    """Convert whole-soil fragment volume to dry mass fraction."""
    _validate(volume_fraction, fine_earth_density, rock_density)
    rock_mass = volume_fraction * rock_density
    return rock_mass / (rock_mass + (1.0 - volume_fraction) * fine_earth_density)


def rock_mass_to_volume_fraction(
    mass_fraction: float, fine_earth_density: float, rock_density: float = 2.65,
) -> float:
    """Convert dry fragment mass to whole-soil volume fraction."""
    _validate(mass_fraction, fine_earth_density, rock_density)
    rock_volume = mass_fraction / rock_density
    return rock_volume / (rock_volume + (1.0 - mass_fraction) / fine_earth_density)
