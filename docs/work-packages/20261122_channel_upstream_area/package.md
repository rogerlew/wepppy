# Restore channel upstream drainage area

Started 2026-11-23 02:59 UTC. Scientific correctness repair for watershed modelers and operators. Security impact is none. The complexity budget permits a linear traversal of the existing D8 drainage graph, tests and documentation.

The diagonal-intersection run used 195,300 m² at reach 24. Its upstream node receives runoff from 2,947,852 other 30 m cells. Restore the original TOPAZ field contract at the Whitebox producer and verify the Peridot consumer with a small watershed. Keep the TSV schema, Bieger coefficients, units and minimum width compatible. Existing TSVs and derived widths must be regenerated from delineation before reuse. Historical runs require operator selection for reprocessing.

Acceptance requires independent area expectations, generated channel dimensions, a published Peridot commit and reproducible source revisions. See [the tracker](tracker.md).

The operator included SWAT+ geometry in scope after review identified its independent area-selection bug. See [ADR-0158](../../adrs/ADR-0158-channel-upstream-node-area.md), [correctness review](artifacts/20261123_correctness_review.md) and [generated-artifact evidence](artifacts/validation.md). Production migration is a separate operational action. Docker Compose workers need the corrected WBT executable. The manually published registry image pins an older WBT revision in .github/workflows/publish-weppcloud-image.yml and requires a separate protected release-pin promotion.

Implementation and requested validation completed 2026-11-23 04:21 UTC. [WEPPpy PR 729](https://github.com/rogerlew/wepppy/pull/729) contains the SWAT+ consumer change and this package.
