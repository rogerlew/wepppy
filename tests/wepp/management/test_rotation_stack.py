from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.wepp.management.managements import read_management
from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth


REPO_ROOT = Path(__file__).resolve().parents[3]
AG_DIR = REPO_ROOT / "wepppy" / "wepp" / "management" / "data" / "Agriculture"


def _load_management(relative_path: str):
    return read_management(str(AG_DIR / relative_path))


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
