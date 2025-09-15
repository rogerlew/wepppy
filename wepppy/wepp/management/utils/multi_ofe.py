import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from copy import deepcopy


class ManagementMultipleOfeSynth(object):
    """
    Synthesizes a single WEPP management file for a simulation with multiple
    Overland Flow Elements (OFEs) from a stack of individual management objects.

    This class systematically merges scenarios from multiple management files,
    ensuring that all cross-references between sections (e.g., from a Yearly
    scenario to a Plant scenario) remain valid in the final composite file.

    The merging strategy involves:
    1.  Using the first management file in the stack as the base.
    2.  For each subsequent management file:
        a. Prepending a unique prefix (e.g., 'OFE2_') to every scenario name
           to prevent naming collisions.
        b. Updating all internal `ScenarioReference` objects to point to these
           new, unique names.
        c. Appending the uniquely named and correctly referenced scenarios to
           the base management file.
    3.  Updating the main 'Management Section' to reflect the total number of
        OFEs and correctly link each OFE to its respective Initial Condition
        and Yearly scenarios.
    """
    def __init__(self, stack=None):
        if stack is None:
            self.stack = []
        else:
            self.stack = stack

    @property
    def description(self):
        s = ["<wepppy.wepp.management.ManagementMultipleOfeSynth>",
             "This file was synthesized from multiple management files.",
             f"Number of OFEs: {self.num_ofes}",
             "Source Stack:"] + [man.man_fn for man in self.stack]
        s = [f"# {L}" for L in s]
        return '\n'.join(s)

    @property
    def num_ofes(self):
        return len(self.stack)

    def write(self, dst_fn):
        """
        Performs the merge operation and writes the resulting synthesized
        management file to the specified destination path.
        """
        # We need access to the ScenarioReference class for type checking
        from wepppy.wepp.management import ScenarioReference

        if not self.stack:
            raise ValueError("Management stack cannot be empty.")

        # If there's only one management file, just write it out directly.
        if len(self.stack) == 1:
            with open(dst_fn, 'w') as pf:
                pf.write(str(self.stack[0]))
            return

        # Start with a deep copy of the first management file as our base.
        mf = deepcopy(self.stack[0])

        # --- Iterate through the rest of the stack to merge them into the base ---
        for i in range(1, len(self.stack)):
            other = deepcopy(self.stack[i])
            new_ofe_num = i + 1
            prefix = f'OFE{new_ofe_num}_'

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

        # Step 5: Finalize by ensuring all objects reference the final merged parent.
        mf.setroot()

        # Write the complete, synthesized management file.
        with open(dst_fn, 'w') as pf:
            pf.write(str(mf))
        
        # Add a descriptive header to the generated file
        with open(dst_fn, 'r') as pf:
            content = pf.read()
        
        with open(dst_fn, 'w') as pf:
            pf.write(self.description + '\n' + content)
