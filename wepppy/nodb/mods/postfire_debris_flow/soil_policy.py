"""Approved M3 recorded-depth policy, isolated from WEPP soil building.

ADR-0067; docs/production_m3_runtime.md. The offline v1 parser and interval
validator remain canonical; only explicit production material/weight policy
differs. Source rows are never mutated or relabeled in retained snapshots.
"""
from collections import defaultdict
import math
import re

from . import soil_thickness as offline

__all__ = ['POLICY', 'derive_recorded_component', 'derive_recorded_mapunits']
POLICY = 'recorded_depth_v1'


def derive_recorded_component(horizons):
    rows = [dict(row, chkey=offline._key(row['chkey'])) for row in horizons]
    original = offline.derive_component(rows)
    disagreements = sum(
        row.get('hzthk_r') not in (None, '') and
        (offline._number(row.get('hzthk_r')) is None or
         offline._number(row.get('hzdept_r')) is not None and
         offline._number(row.get('hzdepb_r')) is not None and
         offline._number(row.get('hzthk_r')) !=
         offline._number(row['hzdepb_r']) - offline._number(row['hzdept_r']))
        for row in rows)
    audit = dict(source_row_count=len(rows), reported_thickness_conflicts=disagreements,
                 pair_reductions=[])
    # A policy transform must never erase disagreement between stable source IDs.
    if 'duplicate_id_conflict' in original['reason_codes']:
        return {**original, **audit}
    unique = {row['chkey']: row for row in rows}
    groups = defaultdict(list)
    reasons = set()
    for row in unique.values():
        copy = dict(row, hzthk_r=None)
        master, name = str(row.get('desgnmaster') or ''), str(row.get('hzname') or '')
        if master == 'H' and re.fullmatch(r'H[1-9][0-9]*', name):
            copy.update(desgnmaster='C', hzname='C')
            reasons.add('legacy_h_included')
        elif master == 'C' and re.fullmatch(r'\d*Cr[0-9]*', name):
            copy.update(desgnmaster='C', hzname='C')
            reasons.add('weathered_material_included')
        groups[(offline._number(row.get('hzdept_r')),
                offline._number(row.get('hzdepb_r')))].append(copy)
    selected = []
    for (top, bottom), group in groups.items():
        master, name = group[0].get('desgnmaster') or '', group[0].get('hzname') or ''
        pair = (len(group) == 2 and top is not None and bottom is not None and
                0 <= top < bottom and re.fullmatch(r'[OAEBC]+(?:/| and )[OAEBC]+', master)
                and ('/' in name or ' and ' in name) and
                all(row.get('desgnmaster') == master and row.get('hzname') == name
                    and offline.derive_component([dict(row, hzdept_r=0,
                        hzdepb_r=bottom-top)])['status'] == 'valid' for row in group))
        if pair:
            reasons.add('legacy_combination_pair')
            audit['pair_reductions'].append(dict(source_chkeys=sorted(row['chkey'] for row in group),
                                               top_cm=top, bottom_cm=bottom,
                                               reason='legacy_combination_pair'))
        selected.extend(group[:1] if pair else group)
    result = offline.derive_component(selected)
    reasons.update(filter(None, result['reason_codes'].split(';')))
    if disagreements:
        reasons.add('reported_thickness_disagreement')
    # Preserve raw interval diagnostics, including the sum before pair reduction.
    result.update({k: original[k] for k in ('interval_sum_cm', 'interval_union_cm', 'deepest_bottom_cm')})
    result.update(audit, reason_codes=';'.join(sorted(reasons)))
    return result


def derive_recorded_mapunits(components, horizons):
    components, horizons = list(components), list(horizons)
    # Reuse canonical key/ownership checks before deriving with another policy.
    offline.derive_mapunits(components, horizons)
    by_component, groups = defaultdict(list), defaultdict(list)
    for row in horizons:
        by_component[offline._key(row['cokey'])].append(row)
    derived = []
    for component in components:
        ck, mk = offline._key(component['cokey']), offline._key(component['mukey'])
        row = dict(mukey=mk, cokey=ck, compname=component.get('compname'),
                   comppct_r=offline._number(component.get('comppct_r')),
                   **derive_recorded_component(by_component[ck]))
        derived.append(row)
        groups[mk].append(row)
    mapunits = []
    for mk, rows in sorted(groups.items()):
        reasons = set()
        valid_weights = [r for r in rows if r['comppct_r'] is not None and 0 <= r['comppct_r'] <= 100]
        if len(valid_weights) != len(rows):
            reasons.add('invalid_percentage')
        known = sum(r['comppct_r'] for r in valid_weights)
        usable = [r for r in valid_weights if r['status'] == 'valid' and r['comppct_r'] > 0]
        weight = sum(r['comppct_r'] for r in usable)
        nonsoil = sum(r['comppct_r'] for r in valid_weights if r['status'] == 'nonsoil')
        numerator = sum(r['comppct_r'] * r['thickness_cm'] for r in usable)
        if not all(math.isfinite(v) for v in (known, weight, nonsoil, numerator)):
            raise ValueError('Nonfinite component aggregation')
        mean = numerator / weight if weight and not reasons else None
        if known > 100:
            reasons.add('overfull_percentage')
        if known < 100 or weight < known:
            reasons.add('incomplete_components')
        for row in rows:
            if row['comppct_r'] != 0:
                reasons.update(filter(None, row['reason_codes'].split(';')))
        mapunits.append(dict(mukey=mk, mean_cm=mean, known_percentage=known,
                             valid_percentage=weight, nonsoil_percentage=nonsoil,
                             rejected_percentage=known-weight-nonsoil,
                             unreported_percentage=max(0, 100-known),
                             status='available' if mean is not None else 'unavailable',
                             reason_codes=';'.join(sorted(reasons))))
    return derived, mapunits
