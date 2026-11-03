from copy import deepcopy
from pathlib import Path

import pytest

from wepppy.wepp.management import read_management
from wepppy.wepp.management.utils import ManagementMultipleOfeSynth

pytestmark = pytest.mark.unit
FIXTURES = Path(__file__).parent / 'fixtures/ag_fields_rotation_synth'
OATS = FIXTURES / 'oats_spring_conventional.man'
CORN = Path(__file__).resolve().parents[3] / 'wepppy/wepp/management/data/Agriculture/corn,soybean-no till.man'


@pytest.fixture(autouse=True)
def independent_working_directory(tmp_path, monkeypatch):
    # Native/model tests elsewhere may change cwd; fixture inputs are file-relative.
    monkeypatch.chdir(tmp_path)


def timeline(man, ofe=0):
    return [[ref.loop_name for ref in year[ofe].manindx]
            for rotation in man.man.loops for year in rotation.years]


def reload(tmp_path, man):
    path = tmp_path / 'out.man'
    path.write_text(str(man))
    return read_management(str(path))


def test_multiple_rotation_roundtrip_and_exact_expansion(tmp_path):
    man = read_management(str(OATS))
    expected = timeline(man)
    assert timeline(reload(tmp_path, man)) == expected
    expanded = man.build_multiple_year_man(5)
    assert len(timeline(expanded)) == expanded.sim_years == 5
    assert timeline(reload(tmp_path, expanded)) == [expected[i % len(expected)] for i in range(5)]


@pytest.mark.parametrize('deduplicate', [False, True])
def test_mixed_calendars_preserve_downstream_years(tmp_path, deduplicate):
    first = read_management(str(OATS))
    second = read_management(str(CORN))
    man = ManagementMultipleOfeSynth([first, second], deduplicate_scenarios=deduplicate).build()
    actual = reload(tmp_path, man.build_multiple_year_man(5))
    assert len(timeline(actual, 1)) == 5
    expected = timeline(second)
    assert [[name.removeprefix('OFE2_') for name in year] for year in timeline(actual, 1)] == [expected[i % len(expected)] for i in range(5)]


@pytest.mark.parametrize('deduplicate', [False, True])
@pytest.mark.parametrize('pcode', [10, 12])
def test_residue_reference_stays_with_source(tmp_path, deduplicate, pcode):
    first = read_management(str(OATS))
    second = deepcopy(first)
    second.plants[-1].data.hmax = 0.123
    for management in (first, second):
        for op in management.ops:
            if op.data.pcode == 10:
                op.data.pcode = pcode
    man = reload(tmp_path, ManagementMultipleOfeSynth([first, second], deduplicate_scenarios=deduplicate).build())
    plants = {p.name: p for p in man.plants}
    downstream = [op for op in man.ops if op.name.startswith('OFE2_') and op.data.pcode in (10, 12) and hasattr(op.data.iresad, 'loop_name')]
    assert downstream
    assert all(plants[op.data.iresad.loop_name].data.hmax == 0.123 for op in downstream)


def test_bounded_requested_years_do_not_materialize_common_period(tmp_path):
    source = read_management(str(CORN))
    first = source.build_multiple_year_man(991)
    second = source.build_multiple_year_man(997)
    path = tmp_path / 'bounded.man'
    ManagementMultipleOfeSynth([first, second]).write(str(path), sim_years=3)
    merged = read_management(str(path))
    assert merged.sim_years == 3
    assert len(timeline(reload(tmp_path, merged))) == 3
    with pytest.raises(ValueError, match='10000'):
        ManagementMultipleOfeSynth([first, second]).build()


def test_pmet_all_crops_and_mapping_idempotence(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    man = read_management(str(OATS))
    (tmp_path / 'p1.man').write_text(str(man))
    names = [plant.name for plant in man.plants]
    kcb = {name: 0.2 + i * 0.1 for i, name in enumerate(names)}
    rawp = {name: 0.6 for name in names}
    pmetpara_prep(str(tmp_path), kcb, rawp)
    first = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    readback = read_management(str(tmp_path / 'p1.man'))
    rows = {row.split(',')[0]: float(row.split(',')[1]) for row in (tmp_path / 'pmetpara.txt').read_text().splitlines()[1:]}
    assert len(rows) == len(names)
    assert all(value == pytest.approx(kcb[readback._pmet_plant_names[alias]["original"]])
               for alias, value in rows.items())
    assert all(len(plant.name) <= 8 and plant.name in rows for plant in readback.plants)
    pmetpara_prep(str(tmp_path), kcb, rawp)
    assert first == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    kcb[names[0]] = 0.9
    pmetpara_prep(str(tmp_path), kcb, rawp)
    assert ',0.9,' in (tmp_path / 'pmetpara.txt').read_text()


def test_pmet_shared_scenario_different_ofe_coefficients(tmp_path):
    from wepppy.wepp.management.pmetpara import _write_prepared_pmet
    source = read_management(str(CORN))
    man = ManagementMultipleOfeSynth([source, source], deduplicate_scenarios=True).build()
    path = tmp_path / 'p1.man'
    path.write_text(str(man))
    _write_prepared_pmet(str(tmp_path), lambda path, ofe, name: (0.3 + ofe * 0.4, 0.6, '-'))
    result = read_management(str(path))
    rows = {row.split(',')[0]: float(row.split(',')[1]) for row in (tmp_path / 'pmetpara.txt').read_text().splitlines()[1:]}
    years = {year.name: year for year in result.years}
    for rotation in result.man.loops:
        for year in rotation.years:
            for ofe, data in enumerate(year):
                assert all(rows[years[ref.loop_name].data.itype.loop_name] == pytest.approx(0.3 + ofe * 0.4) for ref in data.manindx)
    before = path.read_bytes()
    _write_prepared_pmet(str(tmp_path), lambda path, ofe, name: (0.3 + ofe * 0.4, 0.6, '-'))
    assert path.read_bytes() == before


def test_pmet_provenance_survives_read_write_and_detects_loss(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    man = read_management(str(OATS))
    path = tmp_path / 'p1.man'
    path.write_text(str(man))
    kcb = {plant.name: 0.5 for plant in man.plants}
    pmetpara_prep(str(tmp_path), kcb, 0.8)
    path.write_text(str(read_management(str(path))))
    pmetpara_prep(str(tmp_path), kcb, 0.8)
    table = (tmp_path / 'pmetpara.txt').read_bytes()
    path.write_text('\n'.join(line for line in path.read_text().splitlines() if not line.startswith('# MIPA-01')) + '\n')
    with pytest.raises(ValueError, match='Missing PMET identity'):
        pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert (tmp_path / 'pmetpara.txt').read_bytes() == table


@pytest.mark.parametrize('expected', [1, 3])
def test_pmet_mismatched_ofe_counts_fail_before_writes(tmp_path, expected):
    from wepppy.wepp.management.pmetpara import _write_prepared_pmet
    source = read_management(str(CORN))
    man = ManagementMultipleOfeSynth([source, source]).build()
    path = tmp_path / 'p1.man'
    path.write_text(str(man))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='OFE counts disagree'):
        _write_prepared_pmet(str(tmp_path), lambda *args: (0.5, 0.8, '-'), expected_ofes={'p1.man': expected})
    assert path.read_bytes() == before
    assert not (tmp_path / 'pmetpara.txt').exists()


@pytest.mark.parametrize('kind', ['symlink', 'hardlink'])
def test_pmet_never_overwrites_linked_source(tmp_path, kind):
    import os
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    source = tmp_path / 'source.man'
    source.write_text(str(read_management(str(OATS))))
    source.chmod(0o640)
    before = source.read_bytes()
    runs = tmp_path / 'runs'
    runs.mkdir()
    dest = runs / 'p1.man'
    if kind == 'symlink':
        dest.symlink_to(source)
        with pytest.raises(ValueError, match='regular file'):
            pmetpara_prep(str(runs), 0.5, 0.8)
    else:
        os.link(source, dest)
        pmetpara_prep(str(runs), 0.5, 0.8)
        assert dest.stat().st_ino != source.stat().st_ino
        assert dest.stat().st_mode & 0o777 == 0o640
        assert read_management(str(dest)).ncrop == 3
    assert source.read_bytes() == before


def test_pmet_sidecar_symlink_rejected_before_management_publication(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    path = tmp_path / 'p1.man'
    path.write_text(str(read_management(str(OATS))))
    before = path.read_bytes()
    external = tmp_path / 'original.txt'
    external.write_text('original')
    (tmp_path / 'pmetpara.txt').symlink_to(external)
    with pytest.raises(ValueError, match='regular file'):
        pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_bytes() == before
    assert external.read_text() == 'original'


def test_pmet_failed_replace_retains_attempt_and_retry(tmp_path, monkeypatch):
    import wepppy.wepp.management.pmetpara as pmet
    path = tmp_path / 'p1.man'
    path.write_text(str(read_management(str(OATS))))
    before = path.read_bytes()
    replace = pmet.os.replace
    def fail(source, destination):
        raise OSError('injected publication failure')
    monkeypatch.setattr(pmet.os, 'replace', fail)
    with pytest.raises(OSError, match='injected publication'):
        pmet.pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_bytes() == before
    attempts = list(tmp_path.glob('*.mipa-*.tmp'))
    assert len(attempts) == 1
    assert read_management(str(attempts[0])).ncrop == 3
    monkeypatch.setattr(pmet.os, 'replace', replace)
    pmet.pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_bytes() == attempts[0].read_bytes()


def test_pmet_single_ofe_native_safe_control_keeps_management_bytes(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    source = read_management(str(CORN))
    assert all(len(plant.name) <= 8 for plant in source.plants)
    path = tmp_path / 'p1.man'
    path.write_text(str(source))
    before = path.read_bytes()
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_bytes() == before
    assert int((tmp_path / 'pmetpara.txt').read_text().splitlines()[0]) == source.ncrop


@pytest.mark.parametrize('name', ['long_crop_name', 'crop name,one', 'é草', 'crop"one'])
def test_pmet_unsafe_crop_names_have_stable_native_aliases(tmp_path, name):
    import re
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth
    from wepppy.wepp.management.managements import SectionType
    man = read_management(str(CORN))
    old = man.plants[0].name
    walker = ManagementRotationSynth([man])
    for section in (man.inis, man.years, man.ops):
        for loop in section:
            for ref in walker._iter_references(loop):
                if ref.section_type == SectionType.Plant and ref.loop_name == old:
                    ref.loop_name = name
    man.plants[0].name = name
    (tmp_path / 'p1.man').write_text(str(man))
    coefficients = {p.name: 0.2 + i * 0.1 for i, p in enumerate(man.plants)}
    pmetpara_prep(str(tmp_path), coefficients, 0.6)
    result = read_management(str(tmp_path / 'p1.man'))
    assert all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,7}', p.name) for p in result.plants)
    assert name in [record['original'] for record in result._pmet_plant_names.values()]
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    pmetpara_prep(str(tmp_path), coefficients, 0.6)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_pmet_preserves_safe_duplicate_labels_with_distinct_numeric_scenarios(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    text = CORN.read_text()
    source = read_management(str(CORN))
    assert len(source.plants) >= 2
    # Replace only the plant label; the original native numeric references stay
    # distinct. Identical coefficients need no name-keyed graph rewrite.
    text = text.replace(source.plants[1].name, source.plants[0].name)
    path = tmp_path / 'p1.man'
    path.write_text(text)
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_text() == text
    assert (tmp_path / 'pmetpara.txt').read_text().splitlines()[0] == '1'


@pytest.mark.parametrize('mode', ['mofe', 'deduplicated', 'rotation'])
def test_prepared_crop_provenance_survives_synthesis_and_pmet(tmp_path, mode):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    from wepppy.wepp.management.utils.rotation_stack import ManagementRotationSynth
    path = tmp_path / 'p1.man'
    path.write_text(str(read_management(str(OATS))))
    pmetpara_prep(str(tmp_path), 0.3, 0.6)
    prepared = read_management(str(path))
    other = read_management(str(CORN))
    expected = {r['original'] for r in prepared._pmet_plant_names.values()}
    expected.update(p.name for p in other.plants)
    if mode == 'rotation':
        merged = ManagementRotationSynth([prepared, other]).build()
    else:
        merged = ManagementMultipleOfeSynth([prepared, other], deduplicate_scenarios=mode == 'deduplicated').build()
    path.write_text(str(merged))
    reparsed = read_management(str(path))
    assert reparsed._pmet_plant_names
    # Ordinary source names can be prefixed by synthesis; prepared names retain
    # original mapping keys through those same renames.
    mapping = {p.name: 0.5 for p in reparsed.plants}
    mapping.update({name: 0.7 for name in expected})
    pmetpara_prep(str(tmp_path), mapping, 0.6)
    result = read_management(str(path))
    assert expected.intersection(r['original'] for r in result._pmet_plant_names.values()) >= {
        r['original'] for r in prepared._pmet_plant_names.values()}
    before = path.read_bytes()
    pmetpara_prep(str(tmp_path), mapping, 0.6)
    assert path.read_bytes() == before


def test_prepared_same_crop_distinct_definitions_keep_both_ofes(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    path = tmp_path / 'p1.man'
    path.write_text(str(read_management(str(OATS))))
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    first = read_management(str(path))
    second = deepcopy(first)
    active = first.years[0].data.itype.loop_name
    active_index = next(i for i, plant in enumerate(first.plants) if plant.name == active)
    second.plants[active_index].data.hmax = 0.123
    path.write_text(str(ManagementMultipleOfeSynth([first, second]).build()))
    original_names = {r['original'] for r in first._pmet_plant_names.values()}
    coefficients = {name: 0.5 for name in original_names}
    pmetpara_prep(str(tmp_path), coefficients, 0.8)
    result = read_management(str(path))
    matching = [plant for plant in result.plants
                if result._pmet_plant_names[plant.name]['original'] == first._pmet_plant_names[active]['original']]
    assert {plant.data.hmax for plant in matching} == {first.plants[active_index].data.hmax, 0.123}
    assert len({plant.name for plant in matching}) == 2
    year_by_name = {year.name: year for year in result.years}
    plant_by_name = {plant.name: plant for plant in result.plants}
    actual = [plant_by_name[year_by_name[item.manindx[0].loop_name].data.itype.loop_name].data.hmax
              for item in result.man.loops[0].years[0]]
    assert actual == [first.plants[active_index].data.hmax, 0.123]
    before = path.read_bytes()
    pmetpara_prep(str(tmp_path), coefficients, 0.8)
    assert path.read_bytes() == before


def test_prepared_crop_description_only_difference_keeps_native_definition(tmp_path):
    from wepppy.wepp.management.pmetpara import pmetpara_prep
    path = tmp_path / 'p1.man'
    path.write_text(str(read_management(str(OATS))))
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    first = read_management(str(path))
    second = deepcopy(first)
    second.plants[0].description[0] = 'Independent source description'
    path.write_text(str(ManagementMultipleOfeSynth([first, second]).build()))
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    result = read_management(str(path))
    assert result.nofe == 2
    assert result.ncrop == first.ncrop
    before = path.read_bytes()
    pmetpara_prep(str(tmp_path), 0.5, 0.8)
    assert path.read_bytes() == before
