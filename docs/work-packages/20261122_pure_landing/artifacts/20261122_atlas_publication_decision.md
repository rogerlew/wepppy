# Publish explicitly public Atlas projects

Base revision `758791bef`. The operator approved server-side filtering in
the normal build flow. At the point the compiler builds a location row,
require the run directory's explicit NoDb public designation. Public IDs
and the legacy row format stay intact. The next successful scheduled
generation replaces the previous snapshot for all Atlas consumers. Existing
readers, internal counters, log processing and run-access rules stay intact.
Remove the obsolete bundled static copy because it never rolls over.
See the Run Atlas section of the landing contract. Implementation is pending.

Compile mixed public/private fixtures, change visibility, rebuild, inspect
the actual JSON, check preview and aliases against that artifact, and prove
internal statistics still cover both runs. Preserve last-good publication
and the existing empty Atlas behavior.

When logs from multiple directories share a run ID, require every source
to be explicitly public before publishing their merged row.

Independent correctness and security reviews accepted build rollover.
Both identified merged-source visibility. Check each contributing source
and retain the internal merged statistics. Verify static artifact removal
and distinguish isolated build evidence from a deployed scheduled rollover.
