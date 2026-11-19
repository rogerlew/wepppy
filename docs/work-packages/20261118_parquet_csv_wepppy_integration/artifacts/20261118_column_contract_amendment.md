# Column-width compatibility checkpoint

Status: independently approved by correctness and security reviewers.
Source threshold edits have not started.

Inventory: 156 files, maximum 79 physical columns; three totalwatsed3 files exceed
the standalone 64-column limit. Exact inputs are in column-compatibility.json.
Both reviewers independently verified their hashes and widths. Amend the canonical
integration contract and ADR-0149 to 128 columns, 129 schema elements including
the root. Other limits remain unchanged. No dependency or process is added.

Required implementation gates: exact 128/129-column checks, both compact-footer
root-element checks, real-file bytes and bounded resource usage. This checkpoint
must be committed before any source threshold edit.

Security reviewer verified all three source hashes, physical widths and footer
sizes, and approved the bounded amendment. Wider batches may increase working
memory; unchanged process/page/decode ceilings provide containment.

Correctness reviewer confirmed the amended canonical contract and ADR before
checkpoint commit. No unresolved review blocker; implementation gates remain.
