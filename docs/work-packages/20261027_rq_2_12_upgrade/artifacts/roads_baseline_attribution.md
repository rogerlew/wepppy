# Independent attribution of Roads publication gate failure

Date: 2026-10-27 UTC. The required upgraded broad suite stopped at
`tests/roads/test_roads_publication.py::test_published_results_and_sources_are_current_or_explicitly_stale`
with 6,810 passed, 61 skipped and one failed. Its
[original log](rebuilt-full-pytest.log) remains a failed gate invocation; baseline
attribution does not turn it into a passing full suite or cover unexecuted tests.

## Actual old-runtime reproduction

An independent agent ran the exact failing test using retained original image
`sha256:f03d9c55f49229bd1dfb9f720c420ef2568de7919b132ddd7c735a71f4652bcf`.
The [log](roads-baseline-1.16.2.log) prints installed RQ **1.16.2**, redis-py 6.2.0
and the `/opt/venv` module path before pytest. The test fails with the same
`Unreviewed source drift` assertion: the only differing delta is
`wepppy/nodb/mods/roads/roads.py`, actual SHA256
`bc58f90258044a34bf4614887276735f98256a8cfc5d7d868b68523d01d16978` versus reviewed
`25cbde5447e20110b52e3781a3046b4dda5bc026bc10f64fed68bba150a42201`.
Result: **one failed, two warnings, 10.13s**.

The [Compose override](roads-baseline-compose.yml) defines only a disposable
one-shot test container. Execution uses canonical `wctl run --rm --no-deps`,
read-only image and source mounts, UID1000/GID993, network disabled, and a
temporary `/tmp` filesystem. No installed service, Redis state, project, source
file or publication/staleness metadata changes. The container is removed after
the failed test. Network isolation causes ancillary localhost Redis connection
messages during shared test setup; the test still executes and reaches the
identical source-hash assertion. Those setup messages are not the failure cause.

## Source and preimplementation provenance

[Machine-readable attribution](roads-baseline-attribution.json) compares starting
revision `9231f2427d33b64f971992ac969fd9420c49afd3` to implementation revision
`b5cac8166eaf067ac2ef79c440a82314c114111b`. The
[committed diff](roads-source-base-to-current.diff) is empty for Roads source,
publication test, staleness metadata and provenance metadata. Starting and final
committed `roads.py` both hash to the reviewed `25cb...`; the working-tree copy
hashes to `bc58...` and remains dirty. The test and metadata are byte-identical to
both committed revisions.

The initial session's `git status --short`, before package edits, already listed
`M wepppy/nodb/mods/roads/roads.py`. The standalone preimplementation checkpoint
`b1054fac7` independently retains the disclosure in
`prompts/active/implementation_execplan.md`, section `Surprises & Discoveries`:
the repository already had unrelated Roads edits which must be preserved.
No initial working-tree SHA256 was captured, so this evidence does not claim a
byte-for-byte initial snapshot. The old-runtime reproduction and unchanged
committed migration paths directly establish that the observed publication
failure does not require RQ 2.12.0.

## Boundary

The complementary upgraded-runtime check uses the rebuilt image
`sha256:88a982e44d316824f493c99d0c3a9a3db3e4800feef86ff2c65693677039162b`, with
only `roads.py` overlaid read-only from an exact `git show HEAD:...` temporary
file. Its SHA256 is the reviewed `25cb...`; all remaining source and publication
metadata are the unchanged mounted repository. The
[isolated override](roads-committed-compose.yml) has no network or writable source
mount. This is a test fixture, not a working-tree or live-runtime replacement.

All three tests in `tests/roads/test_roads_publication.py` pass under installed
RQ **2.12.0**: **three passed, two warnings, 9.32s**.
[The log](roads-committed-2.12.0.log) records installed runtime and exact input
SHA256 before pytest. The dirty working-tree source still hashes to `bc58...`
afterwards; the one-shot container was removed. This isolates the cause to the
preexisting source-publication mismatch and proves that committed migration
source satisfies this publication file's assertions on the upgraded image.

No Roads source, publication assertion, reviewed-delta record or report was
amended to make this gate pass. The Roads owner must separately review their
existing source change and refresh its publication evidence as appropriate.
Package completion must state the exact failed full-gate invocation and any
separately validated continuation; it must not report an unqualified full-suite
pass on the user's current working tree.
