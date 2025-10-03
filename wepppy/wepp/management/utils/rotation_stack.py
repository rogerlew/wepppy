"""Utilities for composing multi-year management rotations."""

from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Sequence

from wepppy.wepp.management.managements import Management


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

    def build(self, key: str, desc: str | None = None) -> Management:
        """Return a new Management representing the concatenated rotation."""

        base = deepcopy(self.managements[0])
        base.key = key
        if desc is not None:
            base.desc = desc

        cumulative_years = 0
        combined_years = []
        combined_loops = []

        for member in self.managements:
            if member.nofe != self.nofe:
                raise ValueError(
                    "Management OFE count changed during build; this should not happen."
                )

            member_years = deepcopy(member.years)
            member_man = deepcopy(member.man)

            for yloop in member_years:
                yloop.name = f"{yloop.name}_{cumulative_years + 1}"
                combined_years.append(yloop)
                cumulative_years += 1

            combined_loops.append(member_man)

        base.sim_years = cumulative_years
        base.years.loops = combined_years
        base.man.loops = combined_loops

        return base
