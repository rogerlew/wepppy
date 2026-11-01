# Reproduction and retained evidence

Run from `/home/workdir/wepppy` with Python's `-B` flag. Private study root:
`out/frozen-water-history-20261101`. Native source/build provenance and complete
traces are private; no release binary is promoted. See archive-receipt.json for
the retained archive and manifest. Never write into frozen prior studies.

The execution runner, reader, helper and declaration are bound by freeze.json
and the two exact prereviews named in execution-approval.json. The runner first
verified 978 pinned build members, prepared a private observer, checked 29
synthetic controls, then ran all 12 complete histories. Every process, including
readback, has its own receipt. Full pinned runtime libraries are rechecked for
the new binary in observer-runtime.json.

Read-only reproduction into fresh destinations:

    python -B docs/work-packages/20261101_frozen_water_history_ownership/artifacts/summarize_campaign.py --campaign out/frozen-water-history-20261101/campaign-v1 --out /tmp/frozen-history-summary-new.json
    python -B docs/work-packages/20261101_frozen_water_history_ownership/artifacts/read_clearing_ownership_v3.py --scenario out/frozen-water-history-20261101/campaign-v1/zero-ks1 --out /tmp/frozen-clearing-zero-new

Repeat the second command with normal-ks1 and high-ks1 and fresh destinations.
The copied independent_profile_review.py and independent_clearing_review.py
retain their original CLI and bind raw source-free review results; inspect their
help before use. Structural reader controls accept a fresh `--out` directory.
Supplemental control scripts use explicitly versioned raw destinations and
refuse existing directories.

The first execution reader's physical-validity filter excludes some actual
clearings. Its summaries remain unchanged; readback-amendment.md explains why
V3 supplemental receipts are authoritative for all-clearing identities. Do not
substitute valid-state signature counts for total native assignment counts.
All preparatory failures and superseded readbacks remain retained.

A fresh native replay requires a separately named study root and new exact
source/tool/input declaration and review. Do not rerun the hard-coded campaign
against the completed root or modify its frozen inputs. The private archive
contains preparers, patches, complete build/input evidence and authored source
snapshots needed to establish such a version. No new dependency is needed.
