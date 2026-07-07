import csv
from pathlib import Path

import pytest

from wepppy.nodb.mods.disturbed import (
    Disturbed,
    enrich_route_coefficient_row,
    routing_coefficients_from_row,
    validate_route_coefficient_row,
)
from wepppy.nodb.mods.disturbed.route_coefficients import (
    DISTURBED_ROUTE_COEFFICIENT_DEFAULTS,
    ROUTE_COEFFICIENT_ALL_COLUMNS,
)
from wepppy.wepp.management import OW_LANUSE_1_DATVER, get_management

pytestmark = pytest.mark.unit


def _static_extended_lookup_rows():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "wepppy/nodb/mods/disturbed/data/extended_land_soil_lookup.csv"
    with path.open() as fp:
        reader = csv.DictReader(fp)
        return path, list(reader), list(reader.fieldnames or [])


def _base_lookup_rows():
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv"
    with path.open() as fp:
        reader = csv.DictReader(fp)
        return path, list(reader)


def test_static_extended_lookup_contains_valid_route_coefficients():
    _, rows, fieldnames = _static_extended_lookup_rows()

    assert rows
    assert set(ROUTE_COEFFICIENT_ALL_COLUMNS).issubset(fieldnames)
    for row in rows:
        validate_route_coefficient_row(row)
        assert row["route_coeff_authority_class"] == "operator_calibration"
        assert row["route_coeff_confidence"] == "bounded_class_calibration"


def test_route_coefficient_defaults_cover_active_extended_classes():
    _, rows, _ = _static_extended_lookup_rows()
    active_classes = {row["disturbed_class"] for row in rows}

    assert active_classes
    assert active_classes.issubset(DISTURBED_ROUTE_COEFFICIENT_DEFAULTS)


def test_route_coefficient_defaults_cover_base_lookup_classes():
    _, rows = _base_lookup_rows()
    active_classes = {row["luse"] for row in rows}

    assert active_classes
    assert active_classes.issubset(DISTURBED_ROUTE_COEFFICIENT_DEFAULTS)
    for raw_row in rows:
        row = enrich_route_coefficient_row(dict(raw_row, disturbed_class=raw_row["luse"]))
        validate_route_coefficient_row(row)


def test_enrich_route_coefficient_row_is_texture_invariant_for_active_rows():
    _, rows, _ = _static_extended_lookup_rows()
    by_class = {}

    for raw_row in rows:
        row = enrich_route_coefficient_row(dict(raw_row))
        by_class.setdefault(row["disturbed_class"], set()).add(routing_coefficients_from_row(row))

    assert by_class
    assert all(len(values) == 1 for values in by_class.values())


def test_disturbed_native_management_helper_uses_managements_api():
    source = get_management(42, _map="disturbed")
    legacy_text = str(source)
    row = enrich_route_coefficient_row({"disturbed_class": "forest", "luse": "forest"})

    native = Disturbed.build_openwepp_native_management(source, row)
    native_text = str(native)

    assert str(source) == legacy_text
    assert native.datver == OW_LANUSE_1_DATVER
    assert "4 # Landuse - <NativeCropland>" in native_text
    assert "routing_coefficients" in native_text
    assert native.plants[0].data.routing_coefficients.as_tuple() == pytest.approx(
        routing_coefficients_from_row(row)
    )


def test_disturbed_native_management_writer_writes_ow_lanuse_file(tmp_path):
    source = get_management(118, _map="disturbed")
    row = enrich_route_coefficient_row(
        {"disturbed_class": "forest moderate sev fire", "luse": "forest", "stext": "loam"}
    )
    dst = tmp_path / "p1.man"

    Disturbed.write_openwepp_native_management(source, row, str(dst))

    text = dst.read_text()
    assert text.startswith("ow-lanuse-1\n")
    assert "4 # Landuse - <NativeCropland>" in text
    assert "routing_coefficients\n490.00000 0.40000 0.01600 0.05000 0.20000\n" in text
