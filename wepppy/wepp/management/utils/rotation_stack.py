"""Utilities for composing multi-year management rotations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Sequence

import sys

repo_root = Path(__file__).resolve().parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from wepppy.wepp.management.managements import (
        Loops,
        Management,
        ManagementLoopMan,
        ScenarioReference,
    )
except (ModuleNotFoundError, ImportError):
    import types

    pkg = types.ModuleType('wepppy.wepp')
    pkg.__path__ = [str(Path(__file__).resolve().parents[2])]
    sys.modules['wepppy.wepp'] = pkg

    from wepppy.wepp.management.managements import (
        Loops,
        Management,
        ManagementLoopMan,
        ScenarioReference,
    )


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

    def __init__(self, managements: Sequence[Management]):
        if not managements:
            raise ValueError("At least one management is required.")

        base_nofe = managements[0].nofe
        for m in managements:
            if m.nofe != base_nofe:
                raise ValueError(
                    "All managements must have the same number of OFEs; "
                    f"expected {base_nofe}, got {m.nofe}"
                )

        self.managements = list(managements)
        self.nofe = base_nofe

    @property
    def description(self) -> str:
        lines = [
            "<wepppy.wepp.management.ManagementRotationSynth>",
            "This file was synthesized by concatenating management rotations.",
            f"Total segments: {len(self.managements)}",
            "Source sequence:",
        ]

        for m in self.managements:
            label = getattr(m, 'man_fn', m.key)
            lines.append(f"  {label}")

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
        aggregated = {name: Loops() for name in ('plants', 'ops', 'inis', 'surfs', 'contours', 'drains', 'years')}

        total_years = 0
        timeline_per_ofe = [[] for _ in range(self.nofe)]

        processed_segments = []

        for idx, original in enumerate(self.managements):
            segment = deepcopy(original)
            if idx > 0:
                self._apply_prefix(segment, f"SEG{idx + 1}_")

            processed_segments.append(segment)

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
        with dst_path.open('w', encoding='utf-8', newline='\n') as fp:
            if include_header:
                fp.write(self.description + '\n')
            fp.write(str(management))
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
