"""Executable regressions for the versioned research parser (stdlib only)."""
from pathlib import Path
from decimal import Decimal as D
import argparse
import json
import re
import audit_particle_closure_v2 as v2


def expect_invalid(function, *args):
    try:
        function(*args)
    except ValueError:
        return
    raise AssertionError('Invalid row was accepted')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--canonical-element-source', type=Path,
                    default=Path('/workdir/wepppyo3/wepp_interchange/src/hill_element.rs'))
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    fixture_path = Path(__file__).with_name('review-legacy-element-fixed-width-fixture.json')
    fixture = json.loads(fixture_path.read_text())
    raw = fixture['element_raw']
    fields = v2.parse_element_line(raw, fixture['start_year'])
    assert len(raw.split()) == 25 and len(fields) == 26
    assert fields[8:10] == ['5.000', '17.673']
    assert fields[23:26] == ['0.010', '1.274', '0.000']
    result = v2.compare_event(fixture['pass_tokens'], fields, D(str(fixture['width_m'])))
    assert result['causes'] == []
    assert result['bulk_mass_kg'] == '0.03960'
    assert D(result['class_mass_kg']) == D('0.0388997659700001255329296')
    assert D(result['mass_bound_kg']) == D('0.001980684921500000006489450')
    assert v2.compare_event(fixture['pass_tokens'], raw.split(), D('3.96'))['causes'] == ['class_bulk_mass']

    # Native F6.3 enrichment below ten has leading space: ordinary case agrees.
    start = sum(v2.ELEMENT_WIDTHS[:9])
    ordinary = raw[:start] + ' 7.673' + raw[start + 6:]
    normal = v2.parse_element_line(ordinary, fixture['start_year'])
    assert normal == ordinary.split()
    assert v2.compare_event(fixture['pass_tokens'], normal, D('3.96')) == result
    modified = list(fixture['pass_tokens'])
    modified[20] = '0.92437E+00'
    assert v2.compare_event(modified, fields, D('3.96'))['causes'] == ['fraction_sum']
    modified[20] = '0.10010E+01'
    assert set(v2.compare_event(modified, fields, D('3.96'))['causes']) == {'fraction_sum', 'fraction_above_one'}
    modified = list(fixture['pass_tokens'])
    modified[15] = '0.67027E+01'
    assert v2.compare_event(modified, fields, D('3.96'))['causes'] == ['class_bulk_mass']
    expect_invalid(v2.read_elements, [raw, raw], fixture['start_year'])
    expect_invalid(v2.parse_element_line, raw[:-1], fixture['start_year'])
    expect_invalid(v2.parse_element_line, raw + '1', fixture['start_year'])
    expect_invalid(v2.parse_element_line, raw[:3] + ' 32' + raw[6:], fixture['start_year'])
    expect_invalid(v2.parse_element_line, '  0' + raw[3:], fixture['start_year'])
    offset = sum(v2.ELEMENT_WIDTHS[:23])
    for bad in ('      nan', ' ********', '         '):
        expect_invalid(v2.parse_element_line, raw[:offset] + bad + raw[offset + 9:], fixture['start_year'])
    # All-star Sm is a native unavailable diagnostic, not a particle quantity.
    sm_offset = sum(v2.ELEMENT_WIDTHS[:11])
    missing_sm = raw[:sm_offset] + ' *******' + raw[sm_offset + 8:]
    unavailable = []
    parsed = v2.read_elements([missing_sm], fixture['start_year'], unavailable=unavailable)
    assert len(unavailable) == 1 and unavailable[0]['column'] == 'Sm'
    assert unavailable[0]['token'] == '*******'
    assert v2.compare_event(fixture['pass_tokens'], next(iter(parsed.values())), D('3.96')) == result
    expect_invalid(v2.read_elements, [missing_sm], fixture['start_year'])
    source = args.canonical_element_source.read_text()
    for name, expected in [('ELEMENT_FIELD_WIDTHS', v2.ELEMENT_FIELD_WIDTHS),
                           ('ELEMENT_OPTIONAL_FIELD_WIDTHS', v2.ELEMENT_OPTIONAL_FIELD_WIDTHS)]:
        payload = re.search(r'const ' + name + r':[^=]+?=\s*\[([^]]+)\]', source).group(1)
        assert tuple(map(int, re.findall(r'\d+', payload))) == expected
    receipt = dict(passed=True, checks=20, scope='Exact native adjacent-field regression, ordinary-field parity, unchanged strict failure controls, malformed/duplicate rejection and canonical widths',
                   fixture_sha256=v2.digest(fixture_path), audit_v2_sha256=v2.digest(v2.__file__),
                   regression_script_sha256=v2.digest(__file__),
                   canonical_element_source_sha256=v2.digest(args.canonical_element_source),
                   exact_example=result)
    if args.output:
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
