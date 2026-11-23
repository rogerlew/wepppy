# Restore channel upstream drainage area

Started 2026-11-23 02:59 UTC. Scientific correctness repair for watershed modelers and operators. Security impact is none. The complexity budget permits a linear traversal of the existing D8 drainage graph, tests and documentation.

The diagonal-intersection run used 195,300 m² at reach 24. Its upstream node receives runoff from 2,947,852 other 30 m cells. Restore the original TOPAZ field contract at the Whitebox producer and verify the Peridot consumer with a small watershed. Keep the TSV schema, Bieger coefficients, units and minimum width compatible. Existing TSVs and derived widths must be regenerated from delineation before reuse. Historical runs require operator selection for reprocessing.

Acceptance requires independent area expectations, generated channel dimensions, a published Peridot commit and reproducible source revisions. See [the tracker](tracker.md).
