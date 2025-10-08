"""Utilities for composing multi-year management rotations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import sys

from wepppy.wepp.management.managements import (
    Loops,
    Management,
    ManagementLoopMan,
    ManagementLoopManLoop,
    ScenarioReference,
)

__all__ = [
    'ManagementRotationSynth',
]


@dataclass
class _MergedOperation:
    obj: object
    name: Optional[str]
    day: Optional[int]

@dataclass
class _FirstYearMerge:
    ofe_idx: int
    year_name: Optional[str]
    surf_name: Optional[str]
    operations: List[_MergedOperation]
    event_days: List[int]


class ManagementRotationSynth(object):
    """Append multiple managements end-to-end along the time axis.

    The synthesiser accepts a sequence of ``Management`` instances that represent
    consecutive treatments or crop rotations.  It verifies that each input has
    the same number of OFEs and then builds a new ``Management`` whose yearly
    section and management loops are concatenations of the inputs while sharing
    plant/operation/initial-condition scenarios.

    Parameters
    ----------
    managements : Sequence[Management]
        Ordered sequence of management objects that will be appended in the
        order provided.  Instances may repeat.

    Raises
    ------
    ValueError
        If fewer than one management is provided or if any management in the
        sequence has a different OFE count from the first management.
    """

    _VALID_MODES = ('end-to-end', 'stack-and-merge')

    def __init__(self, managements: Sequence[Management], mode: str = 'end-to-end'):
        if not managements:
            raise ValueError("At least one management is required.")

        base_nofe = managements[0].nofe
        for m in managements:
            if m.nofe != base_nofe:
                raise ValueError(
                    "All managements must have the same number of OFEs; "
                    f"expected {base_nofe}, got {m.nofe}"
                )

        if mode not in self._VALID_MODES:
            raise ValueError(f"mode must be one of {self._VALID_MODES}, got {mode!r}")

        self.managements = list(managements)
        self.nofe = base_nofe
        self.mode = mode
        self.warnings: List[str] = []

    @property
    def description(self) -> str:
        lines = [
            "<wepppy.wepp.management.ManagementRotationSynth>",
            f"Stack mode: {self.mode}",
            "This file was synthesized by combining management rotations.",
            f"Total segments: {len(self.managements)}",
            "Source sequence:",
        ]

        for m in self.managements:
            label = getattr(m, 'man_fn', m.key)
            lines.append(f"  {label}")

        if self.warnings:
            lines.append("Warnings:")
            for msg in self.warnings:
                lines.append(f"  {msg}")

        return '\n'.join(f"# {line}" for line in lines)

    def _apply_prefix(self, management: Management, prefix: str) -> None:
        name_maps = {}

        def rename(section_name):
            loops = getattr(management, section_name)
            mapping = {}
            for loop in loops:
                old = loop.name
                new = f"{prefix}{old}"
                loop.name = new
                mapping[old] = new
            name_maps[section_name] = mapping

        for section in ('plants', 'ops', 'inis', 'surfs', 'contours', 'drains', 'years'):
            rename(section)

        def update_ref(ref, section_name):
            if isinstance(ref, ScenarioReference):
                mapping = name_maps.get(section_name, {})
                if ref.loop_name in mapping:
                    ref.loop_name = mapping[ref.loop_name]

        # Initial conditions reference plants
        for ini in management.inis:
            data = getattr(ini, 'data', None)
            if data and hasattr(data, 'iresd'):
                update_ref(data.iresd, 'plants')

        # Surface effects reference operations
        for surf in management.surfs:
            data = getattr(surf, 'data', None)
            if isinstance(data, Loops):
                for til_op in data:
                    if hasattr(til_op, 'op'):
                        update_ref(til_op.op, 'ops')

        # Year loops reference plant/surface/contour/drain scenarios
        for year in management.years:
            data = getattr(year, 'data', None)
            if data:
                if hasattr(data, 'itype'):
                    update_ref(data.itype, 'plants')
                if hasattr(data, 'tilseq'):
                    update_ref(data.tilseq, 'surfs')
                if hasattr(data, 'conset'):
                    update_ref(data.conset, 'drains')
                if hasattr(data, 'drset'):
                    update_ref(data.drset, 'contours')

        # Management loop references initial conditions and years
        for ref in management.man.ofeindx:
            update_ref(ref, 'inis')

        for rot in management.man.loops:
            for year_list in rot.years:
                for man_loop in year_list:
                    for ref in man_loop.manindx:
                        update_ref(ref, 'years')

    def build(self, key: str | None = None, desc: str | None = None) -> Management:
        self.warnings = []
        if self.mode == 'stack-and-merge':
            return self._build_stack_and_merge(key=key, desc=desc)
        return self._build_end_to_end(key=key, desc=desc)

    def _build_end_to_end(self, key: str | None = None, desc: str | None = None) -> Management:
        aggregated = {name: Loops() for name in ('plants', 'ops', 'inis', 'surfs', 'contours', 'drains', 'years')}

        total_years = 0
        timeline_per_ofe = [[] for _ in range(self.nofe)]

        for idx, original in enumerate(self.managements):
            segment = deepcopy(original)
            if idx > 0:
                self._apply_prefix(segment, f"SEG{idx + 1}_")

            for name, loops in aggregated.items():
                for loop in getattr(segment, name):
                    loops.append(loop)

            for rot in segment.man.loops:
                for year_list in rot.years:
                    total_years += 1
                    for ofe_idx, man_loop in enumerate(year_list):
                        copy_loop = deepcopy(man_loop)
                        copy_loop._year = total_years
                        copy_loop._ofe = ofe_idx + 1
                        timeline_per_ofe[ofe_idx].append(copy_loop)

        if any(len(seq) != total_years for seq in timeline_per_ofe):
            raise ValueError("Mismatch while stacking management loops; inconsistent year counts detected.")

        result = deepcopy(self.managements[0])
        if key is not None:
            result.key = key
        if desc is not None:
            result.desc = desc

        result.plants = aggregated['plants']
        result.ops = aggregated['ops']
        result.inis = aggregated['inis']
        result.surfs = aggregated['surfs']
        result.contours = aggregated['contours']
        result.drains = aggregated['drains']
        result.years = aggregated['years']
        result.sim_years = total_years

        # Build a single rotation covering the full timeline
        new_man_loop = ManagementLoopMan.__new__(ManagementLoopMan)
        new_man_loop.root = result
        new_man_loop.parent = result.man
        new_man_loop.years = Loops()

        for year_idx in range(total_years):
            per_ofe = Loops()
            for ofe_idx in range(self.nofe):
                loop = timeline_per_ofe[ofe_idx][year_idx]
                loop.parent = new_man_loop
                per_ofe.append(loop)
            new_man_loop.years.append(per_ofe)

        result.man.loops = Loops()
        result.man.loops.append(new_man_loop)
        result.man.nofes = self.nofe

        self._validate_year_references(result)
        result.setroot()

        return result

    # Helper utilities -------------------------------------------------

    def _segment_label(self, management: Management) -> str:
        if getattr(management, 'man_fn', None):
            return management.man_fn
        if getattr(management, 'key', None):
            return management.key
        return f"{type(management).__name__}"

    def _single_rotation(self, management: Management) -> ManagementLoopMan:
        loops = getattr(management.man, 'loops', None)
        if not loops or len(loops) != 1:
            label = self._segment_label(management)
            raise ValueError(
                f"Segment '{label}' has {0 if not loops else len(loops)} management rotations; "
                "stack-and-merge requires exactly one."
            )
        return loops[0]

    def _capture_first_year_payload(
        self,
        segment: Management,
        rotation: ManagementLoopMan,
    ) -> List[_FirstYearMerge]:
        payload: List[_FirstYearMerge] = []

        if not rotation.years:
            return payload

        first_year = rotation.years[0]
        second_year = rotation.years[1] if len(rotation.years) > 1 else None

        second_year_surf_names: Dict[int, Optional[str]] = {}
        if second_year:
            for ofe_idx, man_loop in enumerate(second_year):
                year_name = self._first_year_ref_name(man_loop.manindx)
                year_loop = self._find_loop(segment.years, year_name)
                surf_name = None
                if year_loop is not None:
                    tilseq = getattr(year_loop.data, 'tilseq', None)
                    if isinstance(tilseq, ScenarioReference):
                        surf_name = tilseq.loop_name or None
                second_year_surf_names[ofe_idx] = surf_name

        for ofe_idx, man_loop in enumerate(first_year):
            year_name = self._first_year_ref_name(man_loop.manindx)
            year_loop = self._find_loop(segment.years, year_name)
            surf_name = None
            operations: List[_MergedOperation] = []
            if year_loop is not None:
                tilseq = getattr(year_loop.data, 'tilseq', None)
                if isinstance(tilseq, ScenarioReference):
                    surf_name = tilseq.loop_name or None
                    if surf_name == '':
                        surf_name = None

            # Avoid duplicating operations when both years reference the same surface scenario.
            same_surface_as_second = (
                surf_name is not None and second_year_surf_names.get(ofe_idx) == surf_name
            )

            if surf_name is not None and not same_surface_as_second:
                surf_loop = self._find_loop(segment.surfs, surf_name)
                if surf_loop is not None:
                    for til_op in getattr(surf_loop, 'data', []):
                        op_copy = deepcopy(til_op)
                        op_name = getattr(getattr(op_copy, 'op', None), 'loop_name', None)
                        day = self._julian_to_int(getattr(op_copy, 'mdate', None))
                        operations.append(_MergedOperation(obj=op_copy, name=op_name, day=day))

            event_days = self._collect_year_event_days(year_loop)

            payload.append(
                _FirstYearMerge(
                    ofe_idx=ofe_idx,
                    year_name=year_name,
                    surf_name=None if same_surface_as_second else surf_name,
                    operations=operations,
                    event_days=event_days,
                )
            )

        return payload

    def _trim_first_year(
        self,
        segment: Management,
        rotation: ManagementLoopMan,
        payload: List[_FirstYearMerge],
    ) -> None:
        if rotation.years:
            del rotation.years[0]

        year_names_to_remove = {item.year_name for item in payload if item.year_name}
        if year_names_to_remove:
            rotation_years = [loop for loop in segment.years if getattr(loop, 'name', None) not in year_names_to_remove]
            segment.years[:] = rotation_years

        # Adjust the simulated year count to reflect the trimmed rotation.
        if getattr(segment, 'sim_years', None) is not None:
            segment.sim_years = max(len(rotation.years), segment.sim_years - 1)

    def _merge_first_year_payload(
        self,
        payload: List[_FirstYearMerge],
        timeline_per_ofe: List[List[ManagementLoopManLoop]],
        year_lookup: Dict[str, Any],
        surf_lookup: Dict[str, Any],
        last_event_day: List[int],
        segment_label: str,
    ) -> None:
        if not payload:
            return

        for item in payload:
            if not timeline_per_ofe[item.ofe_idx]:
                continue

            prev_loop = timeline_per_ofe[item.ofe_idx][-1]
            target_year_name = self._first_year_ref_name(prev_loop.manindx)
            if not target_year_name:
                continue

            target_year_loop = year_lookup.get(target_year_name)
            if target_year_loop is None:
                continue

            tilseq = getattr(target_year_loop.data, 'tilseq', None)
            if not isinstance(tilseq, ScenarioReference):
                continue
            target_surf = surf_lookup.get(tilseq.loop_name)
            if target_surf is None:
                continue

            if item.surf_name is None and not item.event_days:
                continue

            if item.operations:
                for op_payload in item.operations:
                    if hasattr(target_surf, 'data'):
                        target_surf.data.append(op_payload.obj)
                    if hasattr(target_surf, 'ntill') and isinstance(target_surf.ntill, int):
                        target_surf.ntill += 1

                    if op_payload.day is not None:
                        if op_payload.day < last_event_day[item.ofe_idx]:
                            op_label = op_payload.name or 'operation'
                            self.warnings.append(
                                f"{segment_label} OFE {item.ofe_idx + 1}: "
                                f"{op_label} (day {op_payload.day}) occurs before day {last_event_day[item.ofe_idx]}"
                            )
                        last_event_day[item.ofe_idx] = max(last_event_day[item.ofe_idx], op_payload.day)

            for day in item.event_days:
                if day < last_event_day[item.ofe_idx]:
                    self.warnings.append(
                        f"{segment_label} OFE {item.ofe_idx + 1}: event day {day} occurs before day {last_event_day[item.ofe_idx]}"
                    )
                last_event_day[item.ofe_idx] = max(last_event_day[item.ofe_idx], day)

            if hasattr(target_surf, 'ntill') and isinstance(target_surf.ntill, int):
                # Keep ntill aligned with the actual number of operations.
                target_surf.ntill = len(getattr(target_surf, 'data', []))

    @staticmethod
    def _first_year_ref_name(refs: Iterable[Any]) -> Optional[str]:
        for ref in refs:
            if isinstance(ref, ScenarioReference):
                if ref.loop_name and ref.loop_name != '0':
                    return ref.loop_name
        return None

    def _max_event_day(self, year_loop: Any, surf_loop: Any) -> Optional[int]:
        max_day: Optional[int] = None

        if surf_loop is not None and hasattr(surf_loop, 'data'):
            for til_op in surf_loop.data:
                day = self._julian_to_int(getattr(til_op, 'mdate', None))
                if day is not None:
                    max_day = day if max_day is None else max(max_day, day)

        if year_loop is not None:
            for day in self._collect_year_event_days(year_loop):
                max_day = day if max_day is None else max(max_day, day)

        return max_day

    def _collect_year_event_days(self, year_loop: Any) -> List[int]:
        if year_loop is None:
            return []

        days: List[int] = []
        seen: set[int] = set()

        def visit(obj: Any, attr_name: str = '') -> None:
            if obj is None:
                return
            obj_id = id(obj)
            if obj_id in seen:
                return
            seen.add(obj_id)

            day = self._julian_to_int(obj)
            if day is not None:
                if isinstance(obj, int):
                    name = attr_name.lower()
                    if not (
                        name.startswith('jd')
                        or name.endswith('day')
                        or name.endswith('date')
                        or name in {'gday', 'gend'}
                    ):
                        return
                if 0 < day <= 366:
                    days.append(day)
                return

            if isinstance(obj, Loops) or isinstance(obj, list) or isinstance(obj, tuple):
                for item in obj:
                    visit(item)
                return

            if hasattr(obj, '__dict__'):
                for name, value in vars(obj).items():
                    if name == 'root':
                        continue
                    visit(value, name)

        data = getattr(year_loop, 'data', year_loop)
        visit(data)
        return days

    @staticmethod
    def _julian_to_int(value: Any) -> Optional[int]:
        if value is None or value == '':
            return None
        if isinstance(value, (int, float)):
            day = int(value)
            if 0 <= day <= 366:
                return day
            return None
        julian_value = getattr(value, 'julian', None)
        if julian_value is not None:
            day = int(julian_value)
            if 0 <= day <= 366:
                return day
        return None

    @staticmethod
    def _find_loop(loops: Iterable[Any], name: Optional[str]) -> Optional[Any]:
        if not name:
            return None
        for loop in loops:
            if getattr(loop, 'name', None) == name:
                return loop
        return None

    def _build_stack_and_merge(self, key: str | None = None, desc: str | None = None) -> Management:
        self.warnings = []
        aggregated = {name: Loops() for name in ('plants', 'ops', 'inis', 'surfs', 'contours', 'drains', 'years')}

        total_years = 0
        timeline_per_ofe: List[List[ManagementLoopManLoop]] = [[] for _ in range(self.nofe)]
        year_lookup: Dict[str, object] = {}
        surf_lookup: Dict[str, object] = {}
        last_event_day = [0 for _ in range(self.nofe)]

        for idx, original in enumerate(self.managements):
            segment = deepcopy(original)
            if idx > 0:
                self._apply_prefix(segment, f"SEG{idx + 1}_")

            rotation = self._single_rotation(segment)
            nyears = rotation.nyears
            if nyears not in (1, 2):
                label = self._segment_label(original)
                raise ValueError(
                    f"Segment '{label}' has {nyears} years; stack-and-merge mode requires 1 or 2 years."
                )

            first_year_payload: List[_FirstYearMerge] = []
            if nyears == 2:
                first_year_payload = self._capture_first_year_payload(segment, rotation)
                self._trim_first_year(segment, rotation, first_year_payload)

                if total_years > 0:
                    self._merge_first_year_payload(
                        payload=first_year_payload,
                        timeline_per_ofe=timeline_per_ofe,
                        year_lookup=year_lookup,
                        surf_lookup=surf_lookup,
                        last_event_day=last_event_day,
                        segment_label=self._segment_label(original),
                    )

            for name, loops in aggregated.items():
                section_loops = getattr(segment, name)
                for loop in section_loops:
                    loops.append(loop)
                    if name == 'years':
                        year_lookup[loop.name] = loop
                    elif name == 'surfs':
                        surf_lookup[loop.name] = loop

            for year_list in rotation.years:
                total_years += 1
                for ofe_idx, man_loop in enumerate(year_list):
                    copy_loop = deepcopy(man_loop)
                    copy_loop._year = total_years
                    copy_loop._ofe = ofe_idx + 1
                    timeline_per_ofe[ofe_idx].append(copy_loop)

                for ofe_idx, man_loop in enumerate(year_list):
                    year_name = self._first_year_ref_name(man_loop.manindx)
                    year_loop = year_lookup.get(year_name) if year_name else None
                    surf_loop = None
                    if year_loop is not None:
                        tilseq = getattr(year_loop.data, 'tilseq', None)
                        if isinstance(tilseq, ScenarioReference) and tilseq.loop_name:
                            surf_loop = surf_lookup.get(tilseq.loop_name)
                    max_day = self._max_event_day(year_loop, surf_loop)
                    if max_day is not None:
                        last_event_day[ofe_idx] = max_day

        if total_years == 0:
            raise ValueError("No years were produced during stack-and-merge synthesis.")

        if any(len(seq) != total_years for seq in timeline_per_ofe):
            raise ValueError("Mismatch while stacking management loops; inconsistent year counts detected.")

        result = deepcopy(self.managements[0])
        if key is not None:
            result.key = key
        if desc is not None:
            result.desc = desc

        result.plants = aggregated['plants']
        result.ops = aggregated['ops']
        result.inis = aggregated['inis']
        result.surfs = aggregated['surfs']
        result.contours = aggregated['contours']
        result.drains = aggregated['drains']
        result.years = aggregated['years']
        result.sim_years = total_years

        new_man_loop = ManagementLoopMan.__new__(ManagementLoopMan)
        new_man_loop.root = result
        new_man_loop.parent = result.man
        new_man_loop.years = Loops()

        for year_idx in range(total_years):
            per_ofe = Loops()
            for ofe_idx in range(self.nofe):
                loop = timeline_per_ofe[ofe_idx][year_idx]
                loop.parent = new_man_loop
                per_ofe.append(loop)
            new_man_loop.years.append(per_ofe)

        result.man.loops = Loops()
        result.man.loops.append(new_man_loop)
        result.man.nofes = self.nofe

        self._validate_year_references(result)
        result.setroot()

        return result

    def write(
        self,
        dst_path: str | Path,
        key: str | None = None,
        desc: str | None = None,
        include_header: bool = True,
    ) -> Path:
        dst_path = Path(dst_path)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        management = self.build(key or dst_path.stem, desc)

        man_text = str(management)
        if include_header:
            lines = man_text.splitlines()
            if lines:
                lines = [lines[0], self.description, *lines[1:]]
            else:
                lines = [self.description]
            man_text = '\n'.join(lines)

        if not man_text.endswith('\n'):
            man_text += '\n'

        with dst_path.open('w', encoding='utf-8', newline='\n') as fp:
            fp.write(man_text)
        return dst_path

    def _validate_year_references(self, management: Management) -> None:
        year_names = {loop.name for loop in management.years}
        if not year_names:
            raise ValueError("Stacked management contains no yearly scenarios.")

        for rot in management.man.loops:
            for year_list in rot.years:
                if len(year_list) != self.nofe:
                    raise ValueError("OFE count mismatch detected while building rotation stack.")
                for man_loop in year_list:
                    for ref in man_loop.manindx:
                        if isinstance(ref, ScenarioReference):
                            if ref.loop_name not in year_names and ref.loop_name != '0':
                                raise ValueError(
                                    f"Year scenario '{ref.loop_name}' referenced in management loop but not defined."
                                )


if __name__ == "__main__":
    import sys
    import types
    from glob import glob

    from wepppy.wepp.management.managements import read_management

    base_dir = Path('/wc1/runs/du/dumbfounded-patentee/ag_fields/plant_files')
    stack = [read_management(fn) for fn in sorted(glob(str(base_dir / '2017.1/*.man')))]

    synth = ManagementRotationSynth(stack)
    synth.write(
        base_dir / 'test_rotation' / 'test_rotation.man',
        key='test_rotation',
        desc='Rotation stack smoke test',
    )
