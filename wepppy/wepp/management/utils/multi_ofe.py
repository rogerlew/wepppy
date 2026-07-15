"""Utilities for synthesizing multi-OFE WEPP management files."""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, Iterable, List, Optional

if False:  # pragma: no cover - typing only
    from wepppy.wepp.management.managements import Management


class ManagementMultipleOfeSynth(object):
    """Compose a single management file from several single-OFE managements."""

    WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS = 32

    def __init__(
        self,
        stack: Optional[Iterable['Management']] = None,
        *,
        deduplicate_scenarios: bool = False,
    ) -> None:
        """
        Parameters
        ----------
        stack:
            Sequence of ``Management`` objects (one per OFE) that will be
            merged into a single multi-OFE management definition.  The first
            entry is treated as the base file.
        """
        self.stack: List['Management'] = list(stack or [])
        self.deduplicate_scenarios = bool(deduplicate_scenarios)

    @property
    def description(self) -> str:
        s = ["<wepppy.wepp.management.ManagementMultipleOfeSynth>",
             "This file was synthesized from multiple management files.",
             f"Number of OFEs: {self.num_ofes}",
             "Source Stack:"] + [man.man_fn for man in self.stack]
        s = [f"# {L}" for L in s]
        return '\n'.join(s)

    @property
    def num_ofes(self) -> int:
        return len(self.stack)

    @staticmethod
    def _collect_referenced_yearly_loop_names(management: 'Management') -> List[str]:
        """Return unique yearly loop names referenced by management rotations."""
        referenced_names: List[str] = []
        seen = set()

        for rotation in management.man.loops:
            for year in rotation.years:
                for ofe in year:
                    for year_ref in ofe.manindx:
                        loop_name = getattr(year_ref, "loop_name", None)
                        if loop_name is None or loop_name in seen:
                            continue
                        referenced_names.append(loop_name)
                        seen.add(loop_name)

        return referenced_names

    @classmethod
    def _compact_yearly_scenarios(
        cls,
        management: 'Management',
        *,
        enforce_yearly_scenario_limit: bool = True,
    ) -> None:
        """
        Cull unreferenced yearly scenarios and enforce WEPP hillslope limits.

        Keeps yearly scenarios that are actually referenced from the management
        section, preserving the existing yearly section order to keep output
        deterministic.
        """
        referenced_names = cls._collect_referenced_yearly_loop_names(management)
        referenced_name_set = set(referenced_names)
        if not referenced_name_set:
            raise ValueError(
                "MOFE synthesis produced no referenced yearly scenarios; cannot serialize "
                "a valid management file."
            )

        available_names = {year_loop.name for year_loop in management.years}
        missing_names = [name for name in referenced_names if name not in available_names]
        if missing_names:
            raise ValueError(
                "MOFE synthesis referenced yearly scenarios that were not defined in "
                f"the yearly section: {missing_names}"
            )

        referenced_count = len(referenced_names)
        if (
            enforce_yearly_scenario_limit
            and referenced_count > cls.WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS
        ):
            raise ValueError(
                "MOFE synthesis produced "
                f"{referenced_count} referenced yearly scenarios, exceeding the WEPP "
                "hillslope limit of "
                f"{cls.WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS} "
                "(nmscen must be between 1 and "
                f"{cls.WEPP_HILLSLOPE_MAX_YEARLY_SCENARIOS})."
            )

        compacted_year_loops = []
        seen_compacted = set()
        for year_loop in management.years:
            if year_loop.name not in referenced_name_set or year_loop.name in seen_compacted:
                continue
            compacted_year_loops.append(year_loop)
            seen_compacted.add(year_loop.name)

        if len(compacted_year_loops) != referenced_count:
            raise ValueError(
                "MOFE yearly scenario compaction failed to preserve all referenced "
                f"scenarios: expected {referenced_count}, got {len(compacted_year_loops)}."
            )

        management.years[:] = compacted_year_loops

    @staticmethod
    def _scenario_fingerprint(scenario) -> str:
        original_name = scenario.name
        scenario.name = "__SCENARIO__"
        try:
            return str(scenario)
        finally:
            scenario.name = original_name

    @classmethod
    def _merge_section_deduplicated(
        cls,
        target_loops,
        source_loops,
        *,
        prefix: str,
    ) -> Dict[str, str]:
        """Merge one scenario section and reuse structurally identical entries."""
        fingerprints = {
            cls._scenario_fingerprint(loop): loop.name for loop in target_loops
        }
        name_map: Dict[str, str] = {}
        for loop in source_loops:
            old_name = loop.name
            fingerprint = cls._scenario_fingerprint(loop)
            canonical_name = fingerprints.get(fingerprint)
            if canonical_name is None:
                canonical_name = f"{prefix}{old_name}"
                loop.name = canonical_name
                target_loops.append(loop)
                fingerprints[fingerprint] = canonical_name
            name_map[old_name] = canonical_name
        return name_map

    @staticmethod
    def _update_reference(reference, name_map: Dict[str, str]) -> None:
        from wepppy.wepp.management import ScenarioReference

        if isinstance(reference, ScenarioReference) and reference.loop_name in name_map:
            reference.loop_name = name_map[reference.loop_name]

    @classmethod
    def _merge_management_deduplicated(
        cls,
        target: 'Management',
        source: 'Management',
        *,
        new_ofe_num: int,
    ) -> None:
        """Append one OFE while reusing equivalent scenario graph nodes."""
        prefix = f'OFE{new_ofe_num}_'
        name_maps: Dict[str, Dict[str, str]] = {}

        source.plants.setroot(target)
        name_maps['plants'] = cls._merge_section_deduplicated(
            target.plants, source.plants, prefix=prefix
        )
        target.setroot()
        for operation in source.ops:
            if hasattr(operation, 'data') and hasattr(operation.data, 'iresad'):
                cls._update_reference(operation.data.iresad, name_maps['plants'])
        source.ops.setroot(target)
        name_maps['ops'] = cls._merge_section_deduplicated(
            target.ops, source.ops, prefix=prefix
        )
        target.setroot()
        source.contours.setroot(target)
        name_maps['contours'] = cls._merge_section_deduplicated(
            target.contours, source.contours, prefix=prefix
        )
        target.setroot()
        source.drains.setroot(target)
        name_maps['drains'] = cls._merge_section_deduplicated(
            target.drains, source.drains, prefix=prefix
        )
        target.setroot()

        for initial in source.inis:
            if hasattr(initial, 'data') and hasattr(initial.data, 'iresd'):
                cls._update_reference(initial.data.iresd, name_maps['plants'])
        source.inis.setroot(target)
        name_maps['inis'] = cls._merge_section_deduplicated(
            target.inis, source.inis, prefix=prefix
        )
        target.setroot()

        for surface in source.surfs:
            if not hasattr(surface, 'data'):
                continue
            for operation in surface.data:
                if hasattr(operation, 'op'):
                    cls._update_reference(operation.op, name_maps['ops'])
        source.surfs.setroot(target)
        name_maps['surfs'] = cls._merge_section_deduplicated(
            target.surfs, source.surfs, prefix=prefix
        )
        target.setroot()

        for yearly in source.years:
            if not hasattr(yearly, 'data'):
                continue
            cls._update_reference(yearly.data.itype, name_maps['plants'])
            cls._update_reference(yearly.data.tilseq, name_maps['surfs'])
            # Preserve the parser's historical conset/drset swap.
            cls._update_reference(yearly.data.conset, name_maps['drains'])
            cls._update_reference(yearly.data.drset, name_maps['contours'])
        source.years.setroot(target)
        name_maps['years'] = cls._merge_section_deduplicated(
            target.years, source.years, prefix=prefix
        )
        target.setroot()

        target.nofe = new_ofe_num
        target.man.nofes = new_ofe_num
        initial_reference = source.man.ofeindx[0]
        cls._update_reference(initial_reference, name_maps['inis'])
        target.man.ofeindx.append(initial_reference)

        for rotation_index, rotation in enumerate(target.man.loops):
            for year_index, year_ofes in enumerate(rotation.years):
                source_rotation = source.man.loops[rotation_index % len(source.man.loops)]
                source_year = source_rotation.years[year_index % len(source_rotation.years)]
                ofe_data = source_year[0]
                for yearly_reference in ofe_data.manindx:
                    cls._update_reference(yearly_reference, name_maps['years'])
                ofe_data._ofe = new_ofe_num
                year_ofes.append(ofe_data)

    def build(
        self,
        *,
        enforce_yearly_scenario_limit: bool = True,
    ) -> 'Management':
        """Return the synthesized management graph.

        ``enforce_yearly_scenario_limit=False`` is an inventory-only escape
        hatch.  It permits callers to measure a complete graph before choosing
        a compatible WEPP hillslope build; :meth:`write` keeps enforcing the
        currently supported production limit.
        """
        # We need access to the ScenarioReference class for type checking
        from wepppy.wepp.management import ScenarioReference

        if not self.stack:
            raise ValueError("Management stack cannot be empty.")

        # Preserve historical single-stack behavior while still enforcing
        # yearly scenario validity and WEPP limits.
        if len(self.stack) == 1:
            mf = deepcopy(self.stack[0])
            self._compact_yearly_scenarios(
                mf,
                enforce_yearly_scenario_limit=enforce_yearly_scenario_limit,
            )
            mf.setroot()
            return mf

        # Start with a deep copy of the first management file as our base.
        mf = deepcopy(self.stack[0])

        # --- Iterate through the rest of the stack to merge them into the base ---
        for i in range(1, len(self.stack)):
            other = deepcopy(self.stack[i])
            new_ofe_num = i + 1
            prefix = f'OFE{new_ofe_num}_'

            if self.deduplicate_scenarios:
                self._merge_management_deduplicated(
                    mf,
                    other,
                    new_ofe_num=new_ofe_num,
                )
                continue

            # Step 1: Rename all scenarios in 'other' to make them unique
            # and create maps of the old names to the new names.
            name_maps = {}

            def rename_and_map(section_name, section_loops):
                name_map = {}
                if hasattr(section_loops, '__iter__'):
                    for loop in section_loops:
                        old_name = loop.name
                        new_name = f'{prefix}{old_name}'
                        loop.name = new_name
                        name_map[old_name] = new_name
                name_maps[section_name] = name_map

            rename_and_map('plants', other.plants)
            rename_and_map('ops', other.ops)
            rename_and_map('inis', other.inis)
            rename_and_map('surfs', other.surfs)
            rename_and_map('contours', other.contours)
            rename_and_map('drains', other.drains)
            rename_and_map('years', other.years)

            # Step 2: Update all ScenarioReference objects throughout 'other'
            # to point to the new, prefixed scenario names.
            def update_ref(ref, section_name):
                if isinstance(ref, ScenarioReference) and ref.loop_name in name_maps.get(section_name, {}):
                    ref.loop_name = name_maps[section_name][ref.loop_name]

            for ini_loop in other.inis:
                if hasattr(ini_loop, 'data') and hasattr(ini_loop.data, 'iresd'):
                    update_ref(ini_loop.data.iresd, 'plants')

            for surf_loop in other.surfs:
                if hasattr(surf_loop, 'data'):
                    for op_data in surf_loop.data:
                         if hasattr(op_data, 'op'):
                            update_ref(op_data.op, 'ops')

            for year_loop in other.years:
                if hasattr(year_loop, 'data'):
                    data = year_loop.data
                    update_ref(data.itype, 'plants')
                    update_ref(data.tilseq, 'surfs')
                    # Note: The provided parser swaps conset and drset. This code respects that implementation.
                    update_ref(data.conset, 'drains')
                    update_ref(data.drset, 'contours')

            # Step 3: Append the now-unique scenarios from 'other' to the base 'mf'.
            mf.plants.extend(other.plants)
            mf.ops.extend(other.ops)
            mf.inis.extend(other.inis)
            mf.surfs.extend(other.surfs)
            mf.contours.extend(other.contours)
            mf.drains.extend(other.drains)
            mf.years.extend(other.years)

            # Step 4: Update the final Management section to include the new OFE.
            mf.nofe = new_ofe_num
            mf.man.nofes = new_ofe_num

            # Append the reference to the new OFE's Initial Condition scenario.
            ini_ref_for_new_ofe = other.man.ofeindx[0]
            update_ref(ini_ref_for_new_ofe, 'inis')
            mf.man.ofeindx.append(ini_ref_for_new_ofe)

            # Append the management data for the new OFE for each year in the rotation.
            for rot_idx, rot in enumerate(mf.man.loops):
                for year_idx, year_ofe_list in enumerate(rot.years):
                    # Find the corresponding management data from 'other'
                    # (handles cases where rotation lengths differ)
                    other_rot = other.man.loops[rot_idx % len(other.man.loops)]
                    other_year_data = other_rot.years[year_idx % len(other_rot.years)]
                    ofe_data_to_add = other_year_data[0] # Assumes single OFE in source file

                    # Update the yearly scenario reference within this data block
                    for manindx_ref in ofe_data_to_add.manindx:
                        update_ref(manindx_ref, 'years')

                    # Update the internal OFE number for comment readability
                    ofe_data_to_add._ofe = new_ofe_num
                    year_ofe_list.append(ofe_data_to_add)

        # Step 5: Remove orphan yearly scenarios and enforce WEPP limits.
        self._compact_yearly_scenarios(
            mf,
            enforce_yearly_scenario_limit=enforce_yearly_scenario_limit,
        )

        # Step 6: Finalize by ensuring all objects reference the final merged parent.
        mf.setroot()
        return mf

    def render(
        self,
        *,
        enforce_yearly_scenario_limit: bool = True,
    ) -> str:
        """Return the synthesized management file text."""
        management = self.build(
            enforce_yearly_scenario_limit=enforce_yearly_scenario_limit,
        )
        rendered = str(management)

        # Preserve historical single-stack serialization.  Multi-OFE output
        # records its source stack after the three native header records; the
        # native parser does not skip leading comments before the version token.
        if len(self.stack) == 1:
            return rendered

        lines = rendered.splitlines(keepends=True)
        return ''.join(lines[:3]) + self.description + '\n' + ''.join(lines[3:])

    def write(self, dst_fn: str) -> None:
        """Merge the stack and write the synthesized management to ``dst_fn``."""
        rendered = self.render()

        # Write the complete, synthesized management file.
        with open(dst_fn, 'w') as pf:
            pf.write(rendered)
