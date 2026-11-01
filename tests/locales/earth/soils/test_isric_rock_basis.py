"""Density-explicit SoilGrids volume-to-WEPP-mass artifact regression."""
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from wepppy.locales.earth.soils.isric import ISRICHorizon, ISRICSoilData, isric_depths

pytestmark = pytest.mark.unit


def horizon_data(volume_percent=20.0, density=1.3):
    return dict(cfvo=volume_percent, bdod=density, cec=10.0, clay=20.0,
                sand=50.0, silt=30.0, soc=2.0, wv0033=30.0, wv1500=10.0)


@pytest.mark.parametrize('volume', [0.0, 5.0, 20.0, 80.0, 100.0])
@pytest.mark.parametrize('density', [0.8, 1.3, 2.0])
def test_horizon_volume_becomes_mass(volume, density):
    horizon = ISRICHorizon('0-5cm', horizon_data(volume, density))
    rock_mass = volume * 2.65
    fine_mass = (100 - volume) * density
    assert horizon.rfg == pytest.approx(100 * rock_mass / (rock_mass + fine_mass))


@pytest.mark.parametrize('volume,density', [(float('nan'), 1.3), (-1, 1.3), (101, 1.3), (20, 0), (20, float('inf'))])
def test_invalid_conversion_fails(volume, density):
    with pytest.raises(ValueError):
        ISRICHorizon('0-5cm', horizon_data(volume, density))


def write_soilgrids_fixture(root: Path):
    """Write real stored-unit rasters, including all extraction requirements."""
    raw = dict(bdod=130, cec=100, clay=200, sand=500, silt=300, cfvo=200,
               soc=20, wv0033=300, wv1500=100, wv0010=350)
    root.mkdir(exist_ok=True)
    for depth in isric_depths:
        for measure, value in raw.items():
            write_raster(root / f'{measure}_{depth}_Q0.5.tif', value)
    write_raster(root / 'wrb_MostProbable.tif', 8)


def write_raster(path, value):
    with rasterio.open(path, 'w', driver='GTiff', width=2, height=2, count=1,
                       dtype='float32', crs='EPSG:4326', transform=from_origin(0, 2, 1, 1), nodata=-9999) as ds:
        ds.write(np.full((1, 2, 2), value, dtype=np.float32))


def test_real_rasters_to_serialized_soil_preserve_rock_basis(tmp_path):
    write_soilgrids_fixture(tmp_path)
    data = ISRICSoilData(str(tmp_path))
    data.wgs_bbox = (0.0, 0.0, 2.0, 2.0)
    extracted = data.extract_soil_data(0.5, 0.5)
    assert extracted['0-5cm']['cfvo'] == 20.0
    assert extracted['0-5cm']['bdod'] == 1.3
    key, summary, _ = data.build_soil(0.5, 0.5, soil_fn='rock.sol')
    assert key and summary
    text = (tmp_path / 'rock.sol').read_text()
    rows = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) == 11 and not line.startswith('#'):
            rows.append(list(map(float, tokens)))
    assert len(rows) == 7  # Crossing 150-300 mm horizon split at 200 mm.
    assert [r[0] for r in rows] == [50, 150, 200, 300, 600, 1000, 2000]
    assert all(r[-1] == pytest.approx(33.8) for r in rows)
    assert all(r[1] == 1.3 for r in rows)
    # Native SCON mass conversion, after existing one-decimal serialization.
    w = rows[0][-1] / 100
    interpreted_v = w * rows[0][1] / (w * rows[0][1] + 2.65 * (1 - w))
    assert abs(interpreted_v - 0.2) < 0.0004
