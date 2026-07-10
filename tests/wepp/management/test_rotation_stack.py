from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppy.wepp.management.managements import read_management
from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth


REPO_ROOT = Path(__file__).resolve().parents[3]
AG_DIR = REPO_ROOT / "wepppy" / "wepp" / "management" / "data" / "Agriculture"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ag_fields_rotation_synth"


def _load_management(relative_path: str):
    return read_management(str(AG_DIR / relative_path))


def _load_p3733_managements():
    manifest = json.loads((FIXTURE_DIR / "p3733_schedule.json").read_text(encoding="utf-8"))
    return manifest, [read_management(str(FIXTURE_DIR / name)) for name in manifest["managements"]]


@pytest.mark.unit
def test_stack_end_to_end_managements() -> None:
    managements = [
        _load_management("corn,soybean-no till.man"),
        _load_management("corn,soybean-fall moldboard plow.man"),
    ]

    synth = ManagementRotationSynth(managements)
    result = synth.build(key="stacked_rotation")

    assert result.nofe == result.man.nofes == 1

    expected_years = sum(len(rot.years) for m in managements for rot in m.man.loops)
    assert result.sim_years == expected_years
    assert result.man.loops[0].nyears == expected_years
    assert len(result.man.loops) == 1

    assert len(result.plants) == sum(len(m.plants) for m in managements)
    assert len(result.ops) == sum(len(m.ops) for m in managements)
    assert len(result.inis) == sum(len(m.inis) for m in managements)
    assert len(result.surfs) == sum(len(m.surfs) for m in managements)
    assert len(result.years) == sum(len(m.years) for m in managements)

    segment_two_names = {loop.name for loop in managements[1].plants}
    assert segment_two_names
    for loop in segment_two_names:
        assert f"SEG2_{loop}" in {p.name for p in result.plants}

    for loop in managements[1].years:
        assert f"SEG2_{loop.name}" in {y.name for y in result.years}

    timeline = []
    for per_ofe in result.man.loops[0].years:
        man_loop = per_ofe[0]
        timeline.extend(ref.loop_name for ref in man_loop.manindx if ref.loop_name)

    first_segment_years = sum(len(rot.years) for rot in managements[0].man.loops)
    assert len(timeline) == expected_years
    assert all(not name.startswith("SEG2_") for name in timeline[:first_segment_years])
    assert all(name.startswith("SEG2_") for name in timeline[first_segment_years:])


@pytest.mark.unit
def test_stack_end_to_end_remaps_residue_plant_indices() -> None:
    first = read_management(str(FIXTURE_DIR / "oats_spring_conventional.man"))
    second = read_management(str(FIXTURE_DIR / "oats_spring_conventional.man"))

    result = ManagementRotationSynth([first, second]).build()

    residue_ops = [operation for operation in result.ops if operation.data.pcode == 10]
    assert [operation.data.iresad.loop_name for operation in residue_ops] == [
        "L179_weed",
        "SEG2_L179_weed",
    ]
    assert str(result)


@pytest.mark.unit
def test_stack_and_merge_drops_first_year() -> None:
    two_year = _load_management("corn,soybean-fall moldboard plow.man")

    synth = ManagementRotationSynth([two_year], mode="stack-and-merge")
    result = synth.build(key="stack_and_merge_single")

    assert result.sim_years == 1
    assert result.man.loops[0].nyears == 1
    year_names = [loop.name for loop in result.years]
    assert "Year 1" not in year_names
    assert len(year_names) == 1
    assert not synth.warnings


@pytest.mark.unit
def test_stack_and_merge_merges_operations() -> None:
    first = _load_management("corn,soybean-fall moldboard plow.man")
    second = _load_management("corn,soybean-fall moldboard plow.man")

    second_year_ref = next(
        ref.loop_name
        for ref in first.man.loops[0].years[1][0].manindx
        if ref.loop_name
    )
    original_second_year_loop = next(loop for loop in first.years if loop.name == second_year_ref)
    original_surf_name = original_second_year_loop.data.tilseq.loop_name
    original_surf = next(loop for loop in first.surfs if loop.name == original_surf_name)
    original_operation_count = len(original_surf.data)

    synth = ManagementRotationSynth([first, second], mode="stack-and-merge")
    result = synth.build(key="stack_and_merge_double")

    assert result.sim_years == 2
    assert result.man.loops[0].nyears == 2
    assert synth.warnings
    assert all("occurs before day" in msg for msg in synth.warnings)

    first_year_ref = next(
        ref.loop_name
        for ref in result.man.loops[0].years[0][0].manindx
        if ref.loop_name
    )
    year_lookup = {loop.name: loop for loop in result.years}
    first_year = year_lookup[first_year_ref]
    surf_name = first_year.data.tilseq.loop_name
    surf_loop = next(loop for loop in result.surfs if loop.name == surf_name)

    assert surf_loop.ntill == len(surf_loop.data)
    assert len(surf_loop.data) > original_operation_count


@pytest.mark.unit
def test_stack_and_merge_emits_warnings_for_out_of_order_operations() -> None:
    base = _load_management("corn,soybean-fall moldboard plow.man")
    modified = _load_management("corn,soybean-fall moldboard plow.man")

    rotation = modified.man.loops[0]
    first_year_name = next(
        ref.loop_name
        for ref in rotation.years[0][0].manindx
        if ref.loop_name
    )
    first_year_loop = next(loop for loop in modified.years if loop.name == first_year_name)
    surf_name = first_year_loop.data.tilseq.loop_name
    surf_loop = next(loop for loop in modified.surfs if loop.name == surf_name)
    for op in surf_loop.data:
        op.mdate = 1

    synth = ManagementRotationSynth([base, modified], mode="stack-and-merge")
    result = synth.build(key="stack_and_merge_warning")

    assert result.sim_years == 2
    assert synth.warnings


@pytest.mark.unit
def test_stack_and_merge_reuses_p3733_scenarios_and_round_trips(tmp_path: Path) -> None:
    manifest, managements = _load_p3733_managements()

    synth = ManagementRotationSynth(managements, mode="stack-and-merge")
    result = synth.build(key="p3733_regression")

    assert manifest["pre_repair_ncrop"] == 50
    assert result.sim_years == manifest["expected_sim_years"] == 17
    assert result.man.loops[0].nyears == 17
    assert result.ncrop == 3
    assert result.nop == 10
    assert result.nini == 1
    assert result.nseq == 17
    assert result.nscen == 17
    residue_ops = [operation for operation in result.ops if operation.data.pcode == 10]
    assert len(residue_ops) == 1
    assert residue_ops[0].data.iresad.loop_name == "L179_weed"
    residue_plant = next(plant for plant in result.plants if plant.name == "L179_weed")
    assert residue_plant.data.hmax == 0.0

    rendered = str(result)
    assert "50 # ncrop" not in rendered

    output_path = tmp_path / "p3733_fixed.man"
    synth.write(output_path, key="p3733_regression")
    reparsed = read_management(str(output_path))
    assert reparsed.sim_years == 17
    assert reparsed.ncrop == 3
    assert reparsed.nop == 10


@pytest.mark.unit
def test_stack_and_merge_preserves_combined_spring_fall_surface() -> None:
    oats = read_management(str(FIXTURE_DIR / "oats_spring_conventional.man"))

    result = ManagementRotationSynth([oats], mode="stack-and-merge").build()

    assert result.sim_years == 1
    assert [year.name for year in result.years] == ["Year 2"]
    retained_surface = result.surfs[0]
    operation_days = [operation.mdate.julian for operation in retained_surface.data]
    assert operation_days == [110, 110, 110, 111, 111, 112, 135, 274]


@pytest.mark.unit
def test_stack_and_merge_rejects_more_than_twenty_distinct_plants(tmp_path: Path) -> None:
    source = read_management(str(FIXTURE_DIR / "canola_spring_mt.man"))
    managements = []
    for index in range(21):
        management = read_management(str(FIXTURE_DIR / "canola_spring_mt.man"))
        management.plants[0].data.bb = source.plants[0].data.bb + index
        managements.append(management)

    output_path = tmp_path / "too_many_plants.man"
    synth = ManagementRotationSynth(managements, mode="stack-and-merge")

    with pytest.raises(ValueError, match=r"[0-9]+ distinct plant scenarios.*limit is 20"):
        synth.write(output_path)
    assert not output_path.exists()
