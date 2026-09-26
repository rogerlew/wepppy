"""Native contour/drainage references survive every uploaded-management reader."""
from pathlib import Path
import json
import shutil

import jsonpickle
import pytest

from wepppy.wepp.management.managements import (
    ContourLoop,
    DrainLoop,
    Management,
    ManagementSummary,
    ScenarioReference,
    SectionType,
    get_management_summary,
)
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth
from wepppy.wepp.single_input import canonical_management, read_uploaded_management


ROOT = Path(__file__).resolve().parents[2]
GRASS = ROOT / "wepppy/wepp/management/data/GeoWEPP/grass.man"
SOIL = ROOT / "wepppy/wepp/soils/soilsdb/data/Forest/Forest loam.sol"
CASES = ("contour-only", "drain-only", "mixed")


def _write_source(path, case, *, variant=0):
    """Use asymmetric counts and values so swapped or stale pointers cannot pass."""
    model = read_uploaded_management(GRASS)
    contour_count = 0 if case == "drain-only" else (2 if case == "mixed" else 1)
    drain_count = 0 if case == "contour-only" else (3 if case == "mixed" else 1)
    for index in range(contour_count):
        records = [f"Contour{index}", "Contour fixture", "(null)", "(null)", "1"]
        records.append(f"{0.01 * (index + 1) + 0.001 * variant} .1 10 .5")
        model.contours.append(ContourLoop(records, model))
    for index in range(drain_count):
        records = [f"Drain{index}", "Drainage fixture", "(null)", "(null)", "1"]
        records.append(f"{0.5 + 0.1 * index + 0.05 * variant} .1 .1 10")
        model.drains.append(DrainLoop(records, model))
    yearly = model.years[0].data
    if contour_count:
        yearly.conset = ScenarioReference(SectionType.Contour, model.contours[-1].name, model, yearly)
    if drain_count:
        yearly.drset = ScenarioReference(SectionType.Drain, model.drains[-1].name, model, yearly)
    model.setroot()
    path.write_text(canonical_management(model))
    return (
        0.01 * contour_count + 0.001 * variant if contour_count else None,
        0.5 + 0.1 * (drain_count - 1) + 0.05 * variant if drain_count else None,
    )


def _assert_active_references(management, expected_by_ofe):
    for rotation in management.man.loops:
        for year in rotation.years:
            assert len(year) == len(expected_by_ofe)
            for ofe, (contour_slope, drain_depth) in zip(year, expected_by_ofe):
                yearly = management.years[int(str(ofe.manindx[0])) - 1].data
                for reference, expected_type, section, attribute, expected in (
                    (yearly.conset, SectionType.Contour, management.contours, "cntslp", contour_slope),
                    (yearly.drset, SectionType.Drain, management.drains, "ddrain", drain_depth),
                ):
                    if expected is None:
                        assert reference.section_type is None
                        assert str(reference) == "0"
                    else:
                        # Import-isolation tests reload managements before jsonpickle
                        # hydrates this summary; compare semantic enum identifiers.
                        assert reference.section_type.name == expected_type.name
                        assert reference.section_type.value == expected_type.value
                        selected = section[int(str(reference)) - 1]
                        assert getattr(selected.data, attribute) == pytest.approx(expected)


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_uploaded_and_catalog_summary_reload_preserve_native_references(tmp_path, case):
    from wepppy.nodb.core.landuse import _materialize_mofe_management_segment

    source = tmp_path / "source.man"
    expected = _write_source(source, case)
    original = source.read_bytes()
    _assert_active_references(read_uploaded_management(source), [expected])
    metadata = dict(
        ManagementFile=source.name,
        ManagementDir=str(tmp_path),
        Description="Reference fixture",
        Color=[0, 0, 0, 255],
    )
    uploaded = ManagementSummary(Key="single-user-defined", **metadata)
    reloaded = jsonpickle.decode(jsonpickle.encode(uploaded))
    _assert_active_references(reloaded.get_management(), [expected])

    # Later catalog remaps in an opted-in project use corrected references too.
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"42": {"Key": 42, **metadata}}))
    catalog = get_management_summary(42, str(mapping), native_scenario_references=True)
    reloaded_catalog = jsonpickle.decode(jsonpickle.encode(catalog))
    _assert_active_references(reloaded_catalog.get_management(), [expected])
    materialized = _materialize_mofe_management_segment({
        "key": "42", "man_fn": source.name, "man_dir": str(tmp_path),
        "desc": "Checked catalog management", "color": (0, 0, 0, 255),
        "single_input_policy": True,
    })
    _assert_active_references(materialized, [expected])
    assert source.read_bytes() == original


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("deduplicate", [False, True])
def test_synthesis_remaps_distinct_contour_and_drainage_references(tmp_path, case, deduplicate):
    stack = []
    expected = []
    for variant in (0, 1):
        source = tmp_path / f"source{variant}.man"
        expected.append(_write_source(source, case, variant=variant))
        stack.append(read_uploaded_management(source))
    combined = tmp_path / "combined.man"
    ManagementMultipleOfeSynth(stack, deduplicate_scenarios=deduplicate).write(str(combined))
    prepared = read_uploaded_management(combined, max_ofes=32)
    assert prepared.nofe == 2
    _assert_active_references(prepared, expected)


@pytest.mark.unit
def test_legacy_reader_keeps_existing_reference_interpretation(tmp_path):
    source = tmp_path / "legacy.man"
    _write_source(source, "mixed")
    model = read_uploaded_management(source)
    # Both indices fit both sections, allowing the historic parser to load it.
    model.years[0].data.drset.loop_name = model.drains[0].name
    source.write_text(canonical_management(model))
    legacy = Management(
        Key="legacy", ManagementFile=source.name, ManagementDir=str(tmp_path),
        Description="Legacy reference fixture", Color=(0, 0, 0, 255),
    )
    assert legacy.years[0].data.conset.section_type == SectionType.Drain
    assert legacy.years[0].data.drset.section_type == SectionType.Contour
    assert str(legacy.years[0].data.conset) == "2"
    assert str(legacy.years[0].data.drset) == "1"


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES)
def test_asymmetric_references_reach_prepared_and_native_consumers(tmp_path, case):
    from types import SimpleNamespace
    from wepp_runner.wepp_runner import make_hillslope_run, run_hillslope
    from wepppy.nodb.core.wepp import prep_multi_ofe_hillslope
    from wepppy.nodb.single_input_artifacts import validate_prepared_single_inputs
    from wepppy.wepp.soils.utils import SoilMultipleOfeSynth

    for directory in ("landuse", "soils", "watershed/slope_files/hillslopes", "wepp/runs", "wepp/output"):
        (tmp_path / directory).mkdir(parents=True)
    source = tmp_path / "source.man"
    expected = _write_source(source, case)
    original = source.read_bytes()
    management = read_uploaded_management(source)
    ManagementMultipleOfeSynth([management] * 2, deduplicate_scenarios=True).write(
        str(tmp_path / "landuse/hill_101.mofe.man")
    )
    SoilMultipleOfeSynth([str(SOIL)] * 2).write(str(tmp_path / "soils/hill_101.mofe.sol"))
    (tmp_path / "watershed/slope_files/hillslopes/hill_101.mofe.slp").write_text(
        "97.5\n2\n180 20\n" + "2 10\n0, 0.1 1, 0.1\n" * 2
    )
    runs = tmp_path / "wepp/runs"
    prep_multi_ofe_hillslope((
        "101", 1, str(tmp_path), str(runs), 2,
        None, 0.42, False, None, False, None, False, None, None, True,
    ))
    prepared = read_uploaded_management(runs / "p1.man", max_ofes=32)
    assert prepared.sim_years == 2
    _assert_active_references(prepared, [expected, expected])
    validate_prepared_single_inputs(
        SimpleNamespace(
            config_get_str=lambda section, key, default=None: "True" if key == "single_user_defined_uploads" else default,
            landuse_instance=SimpleNamespace(mode=5), soils_instance=SimpleNamespace(mode=5),
            watershed_instance=SimpleNamespace(subs_summary={"101": {}}, mofe_nsegments={"101": 2}),
            runs_dir=str(runs), multi_ofe=True,
        ),
        SimpleNamespace(wepp=lambda **_kwargs: 1),
    )
    shutil.copyfile(ROOT / "tests/disturbed/data/test_climate.cli", runs / "p1.cli")
    make_hillslope_run(1, 2, str(runs), reveg=False, wepp_bin="wepp_260803")
    success, wepp_id, _elapsed = run_hillslope(1, str(runs), wepp_bin="wepp_260803")
    assert success and wepp_id == 1
    assert (tmp_path / "wepp/output/H1.loss.dat").stat().st_size > 0
    assert source.read_bytes() == original
