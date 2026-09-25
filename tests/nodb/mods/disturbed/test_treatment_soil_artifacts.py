"""Exercise treatment lookup through real soil writers and WEPP preparation."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import logging

import pytest

import wepppy.nodb.mods.disturbed.disturbed as disturbed_module
from wepppy.nodb.mods.disturbed.disturbed import Disturbed, read_disturbed_land_soil_lookup
from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope, prep_soil
from wepppy.wepp.management import get_management_summary
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = [pytest.mark.integration, pytest.mark.nodb, pytest.mark.slow]

# Four representative layers from the incident's Podzols loam profile. The
# upper 200 mm starts with forest Ksat=50; conversion must replace it with 40.
SOURCE = """9002
# Representative choice-feminist forest soil
Any comments:
1 0
0 'forest' 'loam' 1.5 0.3
'Podzols' 'loam' 4 0.01 0.75 400000 3e-05 1
50 1.0 50 10.0 0.216 0.117 45.7 10.0 39.8 23.6 8.0 0.07427 0.4762 0.005309 1.525 143.8 0.1146 0.2144
150 1.1 50 1.0 0.212 0.11 46.3 9.8 37.0 20.1 10.0 0.07148 0.4511 0.005942 1.522 99.56 0.108 0.2102
200 1.1 50 1.0 0.212 0.108 48.4 9.8 19.0 15.2 10.0 0.07156 0.4518 0.00638 1.515 101.0 0.1079 0.2118
600 1.3 10.79 1.0 0.204 0.098 49.4 9.1 9.2 16.0 10.0 0.06616 0.4058 0.008094 1.501 51.4 0.09681 0.2036
1 10000 0.0001
"""

THINNING = [f"thinning_{c}_{g}" for c in (30, 40, 50, 60, 65, 70) for g in (75, 85, 90, 93)]
THINNING += ["thinning", "thinning-custom", "thinningcustom-mulch_30"]
MULCH = [(f"{v} {s} sev fire-mulch_{level}", f"{v} {s} sev fire")
         for v in ("forest", "shrub", "grass")
         for s in ("low", "moderate", "high") for level in (15, 30, 60)]
CASES = [(value, "thinning") for value in THINNING] + MULCH


@pytest.fixture
def soil_case(disturbed_factory, monkeypatch):
    disturbed, root = disturbed_factory("treatment-soils")
    source = root / "soils/base.sol"
    source.write_text(SOURCE)
    soil = WeppSoilUtil(str(source))
    summary = SimpleNamespace(clay=soil.clay, sand=soil.sand, fname=source.name,
                              desc="base", meta_fn=None, area=0.0, pct_coverage=0.0)
    soils = SimpleNamespace(domsoil_d={"101": "base"}, soils={"base": summary},
                            soils_dir=str(source.parent), locked=nullcontext,
                            logger=logging.getLogger(__name__))
    lookup = read_disturbed_land_soil_lookup(
        str(Path(disturbed_module.__file__).parent / "data/disturbed_land_soil_lookup.csv"))
    monkeypatch.setattr(disturbed_module, "Ron", SimpleNamespace(getInstance=lambda wd: None))
    monkeypatch.setattr(Disturbed, "soils_instance", property(lambda self: soils))
    monkeypatch.setattr(Disturbed, "land_soil_replacements_d", property(lambda self: lookup))
    monkeypatch.setattr(Disturbed, "watershed_instance", property(
        lambda self: SimpleNamespace(hillslope_area=lambda topaz: 1.0)))
    return disturbed, root, soils, lookup


def _generate(soil_case, monkeypatch, treatment, version, mofe):
    disturbed, root, soils, lookup = soil_case
    disturbed._sol_ver = version
    landuse = SimpleNamespace(domlc_d={"101": "treated"},
        domlc_mofe_d={"101": {str(i): "treated" for i in range(1, 6)}},
        managements={"treated": SimpleNamespace(disturbed_class=treatment, sol_path=None)})
    monkeypatch.setattr(Disturbed, "landuse_instance", property(lambda self: landuse))
    prepared = root / "wepp/runs/p10.sol"
    if mofe:
        disturbed.modify_mofe_soils()
        intermediate = root / "soils/hill_101.mofe.sol"
        slope = root / "watershed/slope_files/hillslopes/hill_101.mofe.slp"
        slope.parent.mkdir(parents=True)
        # Slope is copied verbatim by preparation; it is not a model execution fixture.
        slope.write_text("slope copy boundary\n")
        (root / "landuse").mkdir()
        man = get_management_summary("144", "disturbed").get_management()
        ManagementMultipleOfeSynth([man] * 5).write(str(root / "landuse/hill_101.mofe.man"))
        prep_multi_ofe_hillslope(("101", 10, str(root), str(prepared.parent),
            1, 0.0001, 0.75, False, None, False, None, False, None))
    else:
        key = disturbed.modify_soil("101", landuse, soils, lookup)
        intermediate = root / "soils" / soils.soils[key].fname
        prep_soil(("101", str(intermediate), str(prepared), 0.0001, None,
                   0.75, False, None, False, None))
    return intermediate, prepared


@pytest.mark.parametrize("mofe", [False, True], ids=["single", "mofe"])
@pytest.mark.parametrize("version", [9002, 9005])
@pytest.mark.parametrize("treatment,base_class", CASES)
def test_treatment_soil_parameters_reach_prepared_inputs(
    soil_case, monkeypatch, treatment, base_class, version, mofe,
):
    _, root, _, lookup = soil_case
    expected = lookup[("loam", base_class)]
    intermediate, prepared = _generate(soil_case, monkeypatch, treatment, version, mofe)
    component = root / "soils" / f"base-loam-{treatment}.sol"
    for path in {component, intermediate, prepared}:
        soil = WeppSoilUtil(str(path))
        assert soil.obj["datver"] == version
        assert len(soil.obj["ofes"]) == (5 if mofe and path != component else 1)
        for ofe in soil.obj["ofes"]:
            assert ofe["luse"] == base_class
            for key in ("ki", "kr", "shcrit", "ksatadj"):
                assert float(ofe[key]) == pytest.approx(float(expected[key]))
            for horizon in ofe["horizons"]:
                if horizon["solthk"] <= 200:
                    assert float(horizon["ksat"]) == pytest.approx(float(expected["avke"]))
            if version == 9002:
                for key in ("ksatfac", "ksatrec"):
                    assert float(ofe[key]) == pytest.approx(float(expected[key]))


@pytest.mark.parametrize("mofe", [False, True])
def test_thinning_uses_operator_lookup_values(soil_case, monkeypatch, mofe):
    lookup = soil_case[3]
    lookup[("loam", "thinning")].update(kr="0.00007", avke="23")
    _, prepared = _generate(soil_case, monkeypatch, "thinning_30_90", 9002, mofe)
    for ofe in WeppSoilUtil(str(prepared)).obj["ofes"]:
        assert float(ofe["kr"]) == pytest.approx(0.00007)
        assert float(ofe["horizons"][0]["ksat"]) == pytest.approx(23)


@pytest.mark.parametrize("treatment", [None, "", "not-thinning", "Thinning_30_90",
                                      " thinning_30_90", "mulch_30"])
@pytest.mark.parametrize("mofe", [False, True])
def test_nonprefix_lookup_misses_keep_existing_behavior(soil_case, monkeypatch, treatment, mofe):
    _, prepared = _generate(soil_case, monkeypatch, treatment, 9002, mofe)
    for ofe in WeppSoilUtil(str(prepared)).obj["ofes"]:
        assert float(ofe["kr"]) == pytest.approx(0.00003)
        assert float(ofe["horizons"][0]["ksat"]) == pytest.approx(50)
        assert float(ofe["ksatfac"]) == pytest.approx(0 if mofe else 1.5)
