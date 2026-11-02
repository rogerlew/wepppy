"""Experimental SSURGO retention preparation; explicit opt-in, no default migration.

The inverse and eligibility reproduce ADR0127, not a universally admitted law.
This module is a private development patch pending scientific admission.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

POLICY = "ssurgo-volume-inverse-experimental-v1"
SOURCE_FIELDS = ("cokey", "chkey", "dbthirdbar_r", "wthirdbar_r", "wfifteenbar_r",
                 "fraggt10_r", "frag3to10_r", "sieveno10_r", "desgnmaster", "hzdepb_r")


def validate_policy(policy, source_data, source_receipt):
    if policy is None:
        if source_receipt is not None:
            raise ValueError("Source receipt requires explicit retention policy")
        return
    if policy != POLICY or source_data != "Surgo":
        raise ValueError("Experimental retention supports only explicit SSURGO policy")
    if not isinstance(source_receipt, str) or len(source_receipt) != 64 or any(
        c not in "0123456789abcdef" for c in source_receipt
    ):
        raise ValueError("Source acquisition receipt SHA256 required")


def finite(value):
    # Original source fields are numeric from the collection, not string defaults.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def decision(horizon, emitted):
    source = horizon.retention_source
    row = dict(chkey=str(horizon.chkey), source=source,
               branches=dict(horizon.retention_branches), mass_percent=horizon.smr,
               before=dict(fc=horizon.field_cap, wp=horizon.wilt_pt))
    reason, inverse = "prior-exclusion", None
    if emitted:
        rho, fc, wp = (source.get(k) for k in ("dbthirdbar_r", "wthirdbar_r", "wfifteenbar_r"))
        mass = horizon.smr
        if set(horizon.retention_branches.values()) != {"source-capped-mass"}:
            reason = "fallback-unchanged"
        elif not all(finite(v) for v in (rho, fc, wp, mass)):
            reason = "missing-original-input"
        elif not 0 < rho < 2.65:
            reason = "density-assumption-conflict"
        elif not 0 <= mass <= 85:
            reason = "native-cap-conflict"
        elif not 0 < wp < fc:
            reason = "zero-or-unordered-source"
        else:
            w = mass / 100
            share = 2.65 * (1-w) / (rho*w + 2.65*(1-w))
            inverse = dict(fc=fc/100/share, wp=wp/100/share, share=share,
                           screen_porosity=1-rho/2.65)
            reason = ("eligible" if 0 < inverse["wp"] < inverse["fc"] < inverse["screen_porosity"]
                      else "porosity-assumption-conflict")
    row.update(reason=reason, inverse=inverse, emitted=emitted)
    return row


def apply_selected(soil):
    """Called exactly once after component, mask and restrictive-layer selection."""
    if getattr(soil, "retention_policy", None) is None:
        return
    rows = []
    for i, (h, mask) in enumerate(zip(soil.horizons, soil.horizons_mask, strict=True)):
        emitted = bool(mask and (soil.res_lyr_i is None or i < soil.res_lyr_i))
        row = decision(h, emitted)
        if row["reason"] == "eligible" and h.smr != 0:
            h.field_cap, h.wilt_pt = row["inverse"]["fc"], row["inverse"]["wp"]
        row["prepared"] = dict(fc=h.field_cap, wp=h.wilt_pt)
        rows.append(row)
    soil.retention_decisions = rows


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": repr(value)}
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def write_companion(soil, path):
    """Read actual writer output, match final depths and strict rounded FC/WP/BD."""
    from wepppy.wepp.soils.utils import WeppSoilUtil
    path = Path(path)
    _require_marker(path)
    parsed = WeppSoilUtil(str(path)).obj
    if len(parsed["ofes"]) != 1:
        raise ValueError("Expected one source OFE")
    actual = parsed["ofes"][0]["horizons"]
    selected = [(h, d) for h, d in zip(soil.horizons, soil.retention_decisions, strict=True)
                if d["emitted"]]
    expected = []
    previous = 0.0
    for index, (h, d) in enumerate(selected):
        depth = h.hzdepb_r * 10
        if index == len(selected)-1:
            depth = math.ceil(max(210, depth)/200)*200
        if depth <= previous:
            raise ValueError("Nonincreasing source horizon depths")
        endpoints = ([200.0] if previous < 200 < depth else []) + [depth]
        for endpoint in endpoints:
            expected.append((endpoint, h, d))
        previous = depth
    if len(actual) != len(expected):
        raise ValueError("Serialized source row count mismatch")
    rows = []
    for index, (a, (depth, h, d)) in enumerate(zip(actual, expected, strict=True)):
        if (a["solthk"] != depth or a["fc"] != float(f"{h.field_cap:.4f}")
                or a["wp"] != float(f"{h.wilt_pt:.4f}")
                or a["bd"] != float(f"{h.dbthirdbar_r:.2f}")):
            raise ValueError("Serialized retention/depth/density mismatch")
        rows.append(dict(row=index, chkey=d["chkey"], values=a))
    receipt = dict(schema="ssurgo-retention-source-v3", policy=soil.retention_policy,
                   source_receipt_sha256=soil.retention_source_receipt,
                   mukey=str(soil.mukey), cokey=str(soil.majorComponent.cokey),
                   soil_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   decisions=soil.retention_decisions, emitted_rows=rows,
                   lineage=[[dict(mukey=str(soil.mukey), cokey=str(soil.majorComponent.cokey),
                                  chkey=row["chkey"], source_receipt_sha256=soil.retention_source_receipt,
                                  source_row=row["row"], values=row["values"]) for row in rows]],
                   status="experimental-preparation-only")
    with Path(str(path)+".retention.json").open("x") as stream:
        json.dump(_json_safe(receipt), stream, indent=2, allow_nan=False)
        stream.write("\n")


def _require_marker(path):
    markers=[line for line in Path(path).read_text().splitlines()
             if line.startswith('# WEPPPY_RETENTION_POLICY=')]
    if markers != ['# WEPPPY_RETENTION_POLICY='+POLICY]:
        raise ValueError('Derived artifact dropped or changed retention marker')


def load_source_companion(source, _ancestors=frozenset(), *, provenance_root=None):
    source = Path(source)
    # Root authority comes from the caller, never from companion metadata.
    root = source.parent.resolve() if provenance_root is None else Path(provenance_root).resolve()
    resolved = source.resolve()
    if provenance_root is not None and not resolved.is_relative_to(root):
        raise ValueError("Artifact is outside caller-owned provenance root")
    markers = [line for line in source.read_text().splitlines()
               if line.startswith('# WEPPPY_RETENTION_POLICY=')]
    companion_path = Path(str(source)+'.retention.json')
    if not markers and not companion_path.exists() and not companion_path.is_symlink():
        return None
    if not resolved.is_relative_to(root) or source.is_symlink() or companion_path.is_symlink():
        raise ValueError("Opt-in artifact/companion escapes root or uses a symlink")
    source=resolved
    if source in _ancestors:
        raise ValueError("Cyclic retention parent provenance")
    ancestors = _ancestors | {source}
    if markers != ['# WEPPPY_RETENTION_POLICY='+POLICY] or not companion_path.is_file():
        raise ValueError('Opt-in marker requires matching provenance companion')
    companion = json.loads(companion_path.read_text())
    if (companion.get('schema') not in {'ssurgo-retention-source-v3','ssurgo-retention-treatment-v3','ssurgo-retention-stack-v3','ssurgo-retention-stage-v3'}
            or companion.get('policy') != POLICY
            or companion.get('status') != 'experimental-preparation-only'
            or companion.get('soil_sha256') != hashlib.sha256(source.read_bytes()).hexdigest()):
        raise ValueError('Source companion identity mismatch')
    from wepppy.wepp.soils.utils import WeppSoilUtil
    ofes = WeppSoilUtil(str(source)).obj['ofes']
    lineage = companion.get('lineage')
    if not isinstance(lineage,list) or len(lineage) != len(ofes):
        raise ValueError('Source companion OFE lineage mismatch')
    for ofe, records in zip(ofes,lineage,strict=True):
        if [row['values'] for row in records] != ofe['horizons']:
            raise ValueError('Source companion row mismatch')
        for row in records:
            if not all(key in row for key in ('mukey','cokey','chkey','source_receipt_sha256','source_row')):
                raise ValueError('Incomplete source identity')
    _validate_identity_joins(companion, source, ancestors, root)
    return companion


def reject_stale_treatment(source, target):
    """Run during actual MOFE planning, before a cached treatment can be reused."""
    if load_source_companion(source) is not None:
        # Opt-in freshness requires no inspection of existing destination contents.
        _fresh_target(target)
        return
    target = Path(target)
    target_companion = Path(str(target)+'.retention.json')
    target_marked = target.is_file() and any(line.startswith('# WEPPPY_RETENTION_POLICY=') for line in target.read_text().splitlines())
    if target_marked or target_companion.exists() or target_companion.is_symlink():
        raise ValueError('Default source cannot reuse an opt-in treatment target')


def check_treatment_task(task):
    """Validate opt-in source artifacts at the real Disturbed worker boundary."""
    from wepppy.wepp.soils.utils import WeppSoilUtil
    source = Path(task['source_soil_path'])
    companion_path = Path(str(source)+'.retention.json')
    companion = load_source_companion(source)
    reject_stale_treatment(source, task['output_path'])
    if companion is None:
        return None
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    parsed = WeppSoilUtil(str(source)).obj
    if companion['schema'] != 'ssurgo-retention-source-v3' or parsed['datver'] != 7778 or len(parsed['ofes']) != 1:
        raise ValueError('Expected experimental 7778 single source profile')
    rows = parsed['ofes'][0]['horizons']
    if [r['values'] for r in companion['emitted_rows']] != rows:
        raise ValueError('Source companion row mismatch')
    if task['sol_ver'] != 9002:
        raise ValueError('Experimental treatment supports only bounded 9002 path')
    replacements = task.get('replacements') or {}
    if task.get('base_quality') is not None:
        raise ValueError('Non-SSURGO quality publication is unsupported for opt-in retention')
    from wepppy.wepp.soils.utils.wepp_soil_util import _parse_disturbed_bd_override
    if _parse_disturbed_bd_override(replacements.get('bd')) is not None or task['recompute_wp_fc_using_rosetta_on_bd_override']:
        raise ValueError('Density-changing treatment is not admitted for this policy')
    reject_stale_treatment(source,task['output_path'])
    return dict(companion=companion, source_rows=rows, source_soil_sha256=digest,
                source_companion_sha256=hashlib.sha256(companion_path.read_bytes()).hexdigest())


def finish_treatment_task(task, context):
    """Read actual serialized output; reject unadmitted repair or geometry changes."""
    from wepppy.wepp.soils.utils import WeppSoilUtil
    target = Path(task['output_path'])
    _require_marker(target)
    parsed = WeppSoilUtil(str(target)).obj
    if parsed['datver'] != 9002 or len(parsed['ofes']) != 1:
        raise ValueError('Unexpected treatment version/OFE count')
    rows = parsed['ofes'][0]['horizons']
    original = context['source_rows']
    if len(original) != len(rows):
        raise ValueError('Unadmitted treatment geometry change')
    for source_row, derived_row in zip(original,rows,strict=True):
        if any(source_row[k] != derived_row[k] for k in ('solthk','bd','fc','wp','rfg')):
            raise ValueError('Unadmitted treatment retention/density/geometry change')
    receipt = dict(schema='ssurgo-retention-treatment-v3', policy=POLICY,
        source_companion_sha256=context['source_companion_sha256'],
        source_soil_sha256=context['source_soil_sha256'],
        parents=[dict(soil_path=os.path.relpath(Path(task['source_soil_path']).resolve(),target.parent.resolve()),
                      soil_sha256=context['source_soil_sha256'],
                      companion_sha256=context['source_companion_sha256'])],
        soil_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_rows=context['companion']['emitted_rows'], serialized_rows=rows,
        lineage=[[dict(original_row,values=actual) for original_row,actual in
                  zip(context['companion']['lineage'][0],rows,strict=True)]],
        status='experimental-preparation-only')
    with Path(str(target)+'.retention.json').open('x') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')


def _fresh_target(target):
    if (Path(target).exists() or Path(target).is_symlink()
            or Path(str(target)+'.retention.json').exists() or Path(str(target)+'.retention.json').is_symlink()):
        raise FileExistsError('Experimental retention requires fresh output targets')


def prepare_stack(stack, target, preserve_input_format):
    companions = [load_source_companion(path) for path in stack]
    if all(value is None for value in companions):
        for path in stack:
            reject_stale_treatment(path,target)
        return None
    if any(value is None for value in companions) or preserve_input_format:
        raise ValueError('Mixed/default or uploaded experimental stack is unsupported')
    _fresh_target(target)
    # One input per OFE is the actual SoilMultipleOfeSynth contract.
    if any(c['schema'] != 'ssurgo-retention-treatment-v3' or len(c['lineage']) != 1 for c in companions):
        raise ValueError('Experimental stack requires single-OFE treatment inputs')
    return dict(lineage=[c['lineage'][0] for c in companions],
                parents=[dict(soil_path=os.path.relpath(Path(path).resolve(),Path(target).parent.resolve()),soil_sha256=c['soil_sha256'],
                    companion_sha256=hashlib.sha256(Path(str(path)+'.retention.json').read_bytes()).hexdigest())
                    for path,c in zip(stack,companions,strict=True)])


def mark_stack_text(text):
    first,rest=text.split('\n',1)
    return first+'\n# WEPPPY_RETENTION_POLICY='+POLICY+'\n'+rest


def _write_derived(target, schema, lineage, parents, settings=None):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    _require_marker(target)
    parsed=WeppSoilUtil(str(target)).obj
    if parsed['datver'] != 9002 or len(parsed['ofes']) != len(lineage):
        raise ValueError('Derived format/OFE count mismatch')
    actual_lineage=[]
    for ofe, records in zip(parsed['ofes'],lineage,strict=True):
        if len(ofe['horizons']) != len(records):
            raise ValueError('Derived row count mismatch')
        for actual,record in zip(ofe['horizons'],records,strict=True):
            if actual != record['values']:
                raise ValueError('Derived row/order/material mismatch')
        actual_lineage.append([dict(r,values=h) for r,h in zip(records,ofe['horizons'],strict=True)])
    receipt=dict(schema=schema,policy=POLICY,soil_sha256=hashlib.sha256(Path(target).read_bytes()).hexdigest(),
                 lineage=actual_lineage,parents=parents,settings=settings,
                 status='experimental-preparation-only')
    with Path(str(target)+'.retention.json').open('x') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')


def finish_stack(target, context):
    _write_derived(target,'ssurgo-retention-stack-v3',context['lineage'],context['parents'])


def prepare_stage(source, target, *, clip, clip_depth, minimum, preserve_input_format, initial_sat, kslast):
    from copy import deepcopy
    companion=load_source_companion(source)
    if companion is None:
        reject_stale_treatment(source,target)
        return None
    if companion['schema'] != 'ssurgo-retention-stack-v3' or minimum or preserve_input_format:
        raise ValueError('Unsupported experimental final staging path')
    if clip and clip_depth != 700:
        raise ValueError('Experimental staging supports declared 700mm clipping only')
    _fresh_target(target)
    expected=[]
    for records in companion['lineage']:
        mapped=[]
        for record in records:
            row=deepcopy(record)
            depth=row['values']['solthk']
            if clip:
                row['values']['solthk']=min(700.,depth)
            mapped.append(row)
            if clip and depth >= 700:
                break
        expected.append(mapped)
    return dict(lineage=expected,parents=[dict(soil_path=os.path.relpath(Path(source).resolve(),Path(target).parent.resolve()),soil_sha256=companion['soil_sha256'],
        companion_sha256=hashlib.sha256(Path(str(source)+'.retention.json').read_bytes()).hexdigest())],
        settings=dict(initial_sat=initial_sat,kslast=kslast,clip=clip,clip_depth=clip_depth))


def finish_stage(target, context):
    from wepppy.wepp.soils.utils import WeppSoilUtil
    parsed=WeppSoilUtil(str(target)).obj
    settings=context['settings']
    for ofe in parsed['ofes']:
        if ofe['sat'] != float(f"{settings['initial_sat']:.4f}"):
            raise ValueError('Staged initial saturation mismatch')
        if settings['kslast'] is not None and ofe['res_lyr']['kslast'] != settings['kslast']:
            raise ValueError('Staged restrictive conductivity mismatch')
    _write_derived(target,'ssurgo-retention-stage-v3',context['lineage'],context['parents'],settings)


def _is_digest(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _validate_identity_joins(companion, source, ancestors, root):
    """Join identities to source decisions or exact hash-bound parent companions."""
    from copy import deepcopy
    schema=companion['schema']
    lineage=companion['lineage']
    identity_keys={'mukey','cokey','chkey','source_receipt_sha256','source_row','values'}
    for records in lineage:
        if not isinstance(records,list) or not records:
            raise ValueError('Empty or malformed retention row lineage')
        for row in records:
            if not isinstance(row,dict) or set(row)!=identity_keys:
                raise ValueError('Malformed retention identity record')
            if any(not isinstance(row[k],str) or not row[k].isdigit() for k in ('mukey','cokey','chkey')):
                raise ValueError('Invalid source identifier type/value')
            if not _is_digest(row['source_receipt_sha256']):
                raise ValueError('Invalid source receipt digest')
            if type(row['source_row']) is not int or row['source_row']<0:
                raise ValueError('Invalid source row index')
    if schema=='ssurgo-retention-source-v3':
        if len(lineage)!=1 or not _is_digest(companion.get('source_receipt_sha256')):
            raise ValueError('Invalid source companion identity')
        for key in ('mukey','cokey'):
            if not isinstance(companion.get(key),str) or not companion[key].isdigit():
                raise ValueError('Invalid source mapunit/component identity')
        decisions=companion.get('decisions')
        emitted=companion.get('emitted_rows')
        if not isinstance(decisions,list) or not isinstance(emitted,list) or len(emitted)!=len(lineage[0]):
            raise ValueError('Source decision/emitted-row structure mismatch')
        by_key={}
        for d in decisions:
            if not isinstance(d,dict) or not isinstance(d.get('source'),dict):
                raise ValueError('Malformed source decision')
            key=d.get('chkey')
            if key in by_key or key!=str(d['source'].get('chkey')) or str(d['source'].get('cokey'))!=companion['cokey']:
                raise ValueError('Source decision identity mismatch')
            from types import SimpleNamespace
            replay=decision(SimpleNamespace(chkey=key,retention_source=d['source'],
                retention_branches=d['branches'],smr=d['mass_percent'],
                field_cap=d['before']['fc'],wilt_pt=d['before']['wp']),d['emitted'])
            if replay['reason']!=d.get('reason') or replay['inverse']!=d.get('inverse'):
                raise ValueError('Source eligibility decision is internally inconsistent')
            prepared=d['before']
            if d['reason']=='eligible' and d['mass_percent']!=0:
                prepared={k:d['inverse'][k] for k in ('fc','wp')}
            if d['prepared']!=prepared:
                raise ValueError('Source prepared values disagree with decision')
            by_key[key]=d
        for index,(row,e) in enumerate(zip(lineage[0],emitted,strict=True)):
            if (not isinstance(e,dict) or e.get('row')!=index or row['source_row']!=index
                    or row['mukey']!=companion['mukey'] or row['cokey']!=companion['cokey']
                    or row['source_receipt_sha256']!=companion['source_receipt_sha256']
                    or row['chkey']!=e.get('chkey') or row['values']!=e.get('values')):
                raise ValueError('Source emitted identity join mismatch')
            d=by_key.get(row['chkey'])
            if d is None or d.get('emitted') is not True:
                raise ValueError('Unselected source decision reached emitted row')
            if any(row['values'][k]!=float(f"{d['prepared'][k]:.4f}") for k in ('fc','wp')):
                raise ValueError('Source prepared/serialized retention mismatch')
        return
    bindings=companion.get('parents')
    expected_count=len(lineage) if schema=='ssurgo-retention-stack-v3' else 1
    if not isinstance(bindings,list) or len(bindings)!=expected_count:
        raise ValueError('Derived parent binding count mismatch')
    parents=[]
    for binding in bindings:
        if (not isinstance(binding,dict) or not isinstance(binding.get('soil_path'),str)
                or not _is_digest(binding.get('soil_sha256')) or not _is_digest(binding.get('companion_sha256'))):
            raise ValueError('Malformed parent binding')
        path,sidecar=_confined_parent(source.parent,binding['soil_path'],root)
        if (not path.is_file() or not sidecar.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=binding['soil_sha256']
                or hashlib.sha256(sidecar.read_bytes()).hexdigest()!=binding['companion_sha256']):
            raise ValueError('Parent artifact/companion binding mismatch')
        parent=load_source_companion(path,ancestors,provenance_root=root)
        if parent is None:
            raise ValueError('Missing opt-in parent identity')
        parents.append(parent)
    if schema=='ssurgo-retention-treatment-v3':
        parent=parents[0]
        if parent['schema']!='ssurgo-retention-source-v3' or len(lineage)!=1:
            raise ValueError('Treatment parent schema mismatch')
        if (companion.get('source_soil_sha256')!=bindings[0]['soil_sha256']
                or companion.get('source_companion_sha256')!=bindings[0]['companion_sha256']
                or companion.get('source_rows')!=parent['emitted_rows']
                or companion.get('serialized_rows')!=[r['values'] for r in lineage[0]]):
            raise ValueError('Treatment source binding mismatch')
        expected=deepcopy(parent['lineage'])
        if len(expected[0])!=len(lineage[0]):
            raise ValueError('Treatment source row count mismatch')
        for old,new in zip(expected[0],lineage[0],strict=True):
            if any(old['values'][k]!=new['values'][k] for k in ('solthk','bd','fc','wp','rfg')):
                raise ValueError('Treatment source material mismatch')
            old['values']=new['values']
    elif schema=='ssurgo-retention-stack-v3':
        if any(p['schema']!='ssurgo-retention-treatment-v3' or len(p['lineage'])!=1 for p in parents):
            raise ValueError('Stack parent schema mismatch')
        expected=[p['lineage'][0] for p in parents]
    else:
        if parents[0]['schema']!='ssurgo-retention-stack-v3':
            raise ValueError('Stage parent schema mismatch')
        settings=companion.get('settings')
        if (not isinstance(settings,dict) or type(settings.get('clip')) is not bool
                or settings['clip'] and settings.get('clip_depth')!=700):
            raise ValueError('Invalid staged depth settings')
        from wepppy.wepp.soils.utils import WeppSoilUtil
        if not finite(settings.get('initial_sat')) or not 0<=settings['initial_sat']<=1:
            raise ValueError('Invalid staged saturation setting')
        if settings.get('kslast') is not None and not finite(settings['kslast']):
            raise ValueError('Invalid staged conductivity setting')
        for ofe in WeppSoilUtil(str(source)).obj['ofes']:
            if (ofe['sat']!=float(f"{settings['initial_sat']:.4f}")
                    or settings.get('kslast') is not None and ofe['res_lyr']['kslast']!=settings['kslast']):
                raise ValueError('Staged settings disagree with actual artifact')
        expected=[]
        for records in parents[0]['lineage']:
            mapped=[]
            for record in records:
                row=deepcopy(record);depth=row['values']['solthk']
                if settings['clip']: row['values']['solthk']=min(700.,depth)
                mapped.append(row)
                if settings['clip'] and depth>=700: break
            expected.append(mapped)
    if lineage!=expected:
        raise ValueError('Derived identity does not match exact parent lineage')


def _confined_parent(base, relative, root):
    """Resolve portable parent identity within caller-owned authority before reads."""
    candidate=Path(relative)
    if not relative or candidate.is_absolute():
        raise ValueError('Parent identity must be relative to its artifact')
    cursor=base
    for part in candidate.parts:
        if part=='.':
            continue
        cursor=cursor.parent if part=='..' else cursor/part
        if not cursor.is_relative_to(root):
            raise ValueError('Parent identity escapes caller-owned provenance root')
        if cursor.is_symlink():
            raise ValueError('Symlink parent identity is unsupported')
    path=cursor.resolve()
    if not path.is_relative_to(root):
        raise ValueError('Parent identity escapes caller-owned provenance root')
    sidecar=Path(str(path)+'.retention.json')
    if sidecar.is_symlink():
        raise ValueError('Symlink parent companion is unsupported')
    return path,sidecar


def write_exclusive(target, text):
    """Preserve serialized text/umask; reject even raced or dangling destinations."""
    _fresh_target(target)
    with open(target,'x') as stream:
        stream.write(text)
