"""Prepare crop-keyed PMET coefficients and native-safe generated crop identities."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import uuid
from typing import Mapping

from .managements import Management, SectionType
from .utils.rotation_stack import ManagementRotationSynth

__all__ = ['pmetpara_prep']
_SAFE_NAME = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,7}\Z')


def _regular_destination(path):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(mode):
        raise ValueError(f'PMET preparation requires a regular file: {path.name}')
    return stat.S_IMODE(mode)


def _replace_generated_text(path, text):
    """Replace a generated directory entry without modifying a linked source inode."""
    mode = _regular_destination(path)
    temporary = path.with_name(f'{path.name}.mipa-{uuid.uuid4().hex}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    # Failed writes remain visible as attempt files; the normal preparation job
    # records failure. A retry replaces only the intended generated destination.
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        if mode is not None:
            os.fchmod(stream.fileno(), mode)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    _regular_destination(path)
    os.replace(temporary, path)


def _read_prepared_management(path):
    _regular_destination(path)
    man = Management(Key=None, ManagementFile=path.name, ManagementDir=str(path.parent),
                     Description="-", Color=(0, 0, 0, 0), NativeScenarioReferences=True)
    provenance = man._pmet_plant_names or {}
    originals = {alias: record['original'] for alias, record in provenance.items()}
    return man, originals


def _coefficient(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('PMET coefficients must be finite.')
    return number


def _write_prepared_pmet(runs_dir, resolve, *, filenames=None, expected_ofes=None):
    """Resolve (file, OFE, original crop) to coefficients, then publish valid decks.

    All validation/rendering precedes writes. Existing preparation owns failure
    status and retry; no new transaction/publication protocol is introduced.
    """
    paths = sorted(path for path in Path(runs_dir).glob('*.man') if 'pw0' not in path.name)
    if filenames is not None:
        paths = [Path(runs_dir) / name for name in sorted(filenames)]
    documents = []
    identities = set()
    for path in paths:
        man, originals = _read_prepared_management(path)
        if len(man.man.ofeindx) != man.nofe or (expected_ofes is not None and expected_ofes[path.name] != man.nofe):
            raise ValueError(f"Management/assignment OFE counts disagree for {path.name}; rebuild inputs.")
        coefficients = {}
        for ofe in range(man.nofe):
            for plant in man.plants:
                original = originals.get(plant.name, plant.name)
                kcb, rawp, description = resolve(path, ofe, original)
                pair = (_coefficient(kcb), _coefficient(rawp))
                definition = hashlib.sha256((str(plant.landuse) + str(plant.data)).encode()).hexdigest()
                identity = (original, pair, definition)
                identities.add(identity)
                coefficients[ofe, plant.name] = (identity, str(description).replace(',', '_').replace('\n', '_').replace('\r', '_'))
        documents.append((path, man, originals, coefficients))

    # Keep unambiguous native names; reserve them before allocating any alias.
    by_name = {}
    pairs_by_name = {}
    for original, pair, definition in identities:
        by_name.setdefault(original, set()).add((pair, definition))
        pairs_by_name.setdefault(original, set()).add(pair)
    aliases = {}
    occupied = {name for name, pairs in pairs_by_name.items()
                if _SAFE_NAME.fullmatch(name) and len(pairs) == 1}
    for identity in sorted(identities):
        original, pair, definition = identity
        if _SAFE_NAME.fullmatch(original) and len(by_name[original]) == 1:
            aliases[identity] = original
            occupied.add(original)
    for identity in sorted(identities):
        if identity in aliases:
            continue
        nonce = 0
        while True:
            digest = hashlib.sha256(json.dumps([identity, nonce], ensure_ascii=True).encode()).hexdigest()
            name = 'P' + digest[:7]
            if name not in occupied:
                break
            nonce += 1
        aliases[identity] = name
        occupied.add(name)

    rows = {}
    rendered = []
    sections = ((SectionType.Plant, 'plants'), (SectionType.Op, 'ops'),
                (SectionType.Ini, 'inis'), (SectionType.Surf, 'surfs'),
                (SectionType.Contour, 'contours'), (SectionType.Drain, 'drains'),
                (SectionType.Year, 'years'))
    for path, source, originals, coefficients in documents:
        lookup = {kind: {loop.name: loop for loop in getattr(source, attr)} for kind, attr in sections}
        if any(len(year) != source.nofe for rotation in source.man.loops for year in rotation.years):
            raise ValueError(f'Inconsistent management OFE count in {path.name}.')
        if (not originals and all(
                _SAFE_NAME.fullmatch(plant.name) and len(pairs_by_name[plant.name]) == 1
                for ofe in range(source.nofe) for plant in source.plants)):
            # Ordinary unambiguous controls need no management rewrite at all.
            for plant in source.plants:
                identity, description = coefficients[0, plant.name]
                rows[plant.name] = (*identity[1], description)
            continue
        if any(len(lookup[kind]) != len(getattr(source, attr)) for kind, attr in sections):
            raise ValueError(f'Duplicate management scenario names in {path.name}; rebuild inputs.')
        result = deepcopy(source)
        walker = ManagementRotationSynth([source])
        output = {kind: [] for kind, _ in sections}
        cache = {}
        signatures = {kind: {} for kind, _ in sections}
        provenance = {}
        visited_plants = set()

        def bind(reference, ofe):
            kind, old_name = reference.section_type, reference.loop_name
            if kind is None or not old_name or old_name == '0':
                return
            key = kind, old_name, ofe
            if key in cache:
                reference.loop_name = cache[key]
                return
            if old_name not in lookup.get(kind, {}):
                raise ValueError(f'Undefined {kind} scenario {old_name!r} in {path.name}.')
            # Parent pointers are rebound by setroot; do not copy the entire graph
            # recursively for each individual referenced scenario.
            original_loop = lookup[kind][old_name]
            loop = deepcopy(original_loop, {id(source): result})
            if kind == SectionType.Plant:
                identity, description = coefficients[ofe, old_name]
                loop.name = aliases[identity]
                if loop.name != identity[0]:
                    loop.description[2] = "MIPA01 alias; identity in generated header"
                provenance[loop.name] = {'original': identity[0], 'kcb': identity[1][0], 'rawp': identity[1][1]}
                loop._pmet_identity = provenance[loop.name]
                rows[loop.name] = (*identity[1], description)
                visited_plants.add(old_name)
            else:
                for child in walker._iter_references(loop):
                    bind(child, ofe)
                loop.name = '__PMET_SCENARIO__'
            # Deduplicate only after child identity has been bound. Plants include
            # the alias, so different coefficient contexts cannot be collapsed.
            signature = ((loop.name, identity[2]) if kind == SectionType.Plant
                         else (None, walker._scenario_signature(loop)))
            existing = signatures[kind].get(signature)
            if existing is None:
                if kind != SectionType.Plant:
                    loop.name = old_name
                    used = {item.name for item in output[kind]}
                    if loop.name in used:
                        loop.name = f'{old_name}_PMET{len(output[kind]) + 1}'
                        while loop.name in used:
                            loop.name += '_'
                elif any(item.name == loop.name for item in output[kind]):
                    raise ValueError(f'Conflicting plant definitions for {loop.name} in {path.name}.')
                output[kind].append(loop)
                signatures[kind][signature] = loop.name
                existing = loop.name
            cache[key] = existing
            reference.loop_name = existing

        for ofe, initial in enumerate(result.man.ofeindx):
            bind(initial, ofe)
        for rotation in result.man.loops:
            for year in rotation.years:
                if len(year) != source.nofe:
                    raise ValueError(f'Inconsistent management OFE count in {path.name}.')
                for ofe, item in enumerate(year):
                    for reference in item.manindx:
                        bind(reference, ofe)
        # Native infile loads all declared crops, including unused/residue-only
        # definitions. Retain those not reached by the current calendar.
        from .managements import ScenarioReference
        for plant in source.plants:
            if plant.name not in visited_plants:
                reference = ScenarioReference(SectionType.Plant, plant.name)
                bind(reference, 0)
        for kind, attr in sections:
            getattr(result, attr)[:] = output[kind]
        result.setroot()
        result._pmet_plant_names = provenance
        text = str(result)
        rendered.append((path, text))

    table = [str(len(rows))]
    for index, (name, (kcb, rawp, description)) in enumerate(sorted(rows.items()), 1):
        table.append(f'{name},{kcb},{rawp},{index},{description}')
    _regular_destination(Path(runs_dir) / 'pmetpara.txt')
    for path, text in rendered:
        _replace_generated_text(path, text)
    _replace_generated_text(Path(runs_dir) / 'pmetpara.txt', '\n'.join(table) + '\n')


def pmetpara_prep(runs_dir: str, kcb: float | Mapping[str, float], rawp: float | Mapping[str, float]) -> None:
    """Prepare all staged crops, retaining original mapping keys across retries."""
    def resolve(path, ofe, original):
        return (kcb[original] if isinstance(kcb, Mapping) else kcb,
                rawp[original] if isinstance(rawp, Mapping) else rawp, '-')
    _write_prepared_pmet(runs_dir, resolve)
