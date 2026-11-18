# Validation environment scope correction

The earlier broad/focused host driver set
`VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT=/tmp` globally to admit Roads upload fixtures.
That setting also classified unrelated ordinary pytest temporary runs as managed
vector-retention storage. This was a validation-driver scope error, not an Omni or
Roads production regression.

## Controlled evidence

`test_omni_clone_links_directory_shared_inputs` was run without source edits on
both immutable baseline and candidate, using otherwise identical guarded one-off
containers. Each command printed only the two relevant filesystem settings.

| Checkout | Filesystem ID | Filesystem root | Result |
| --- | --- | --- | --- |
| Baseline | dev-wc1 | /wc1 (inherited) | Passed, 9.49 s |
| Candidate | dev-wc1 | /wc1 (inherited) | Passed, 9.80 s |
| Baseline | dev-wc1 | /tmp (driver override) | RecordingRedis.sismember failure, 10.47 s |
| Candidate | dev-wc1 | /tmp (driver override) | RecordingRedis.sismember failure, 10.42 s |

`vector_retention_lifecycle._configured_root` intentionally returns `None` for
paths outside configured storage. The global override caused the ordinary Omni
fixture to enter a retention boundary its recorder does not implement. No Omni
production or test edit is justified by these results.

The original Roads route fixture independently reproduced HTTP 507 for
`test_upload_geojson_multipart_file` under inherited `/wc1`: its temporary upload
path was outside the declared filesystem. That fixture already supplies a fresh
RQ recorder and its own ledger/lease doubles. The bounded repair adds exactly two
fixture-local declarations: filesystem ID `roads-route-test`, filesystem root
`str(tmp_path)`. `monkeypatch` restores both after each test. No global environment
change, stub API expansion, or production edit is needed.

The archive provenance failures in `archive_fixture_failure_class.md` were also
observed under the earlier globally aligned driver. Their per-test cleanup keeps
those ordinary fixtures independent of inherited storage settings; those results
do not establish failures under canonical `/wc1` configuration.

## Final validation

Under inherited canonical settings, the full Roads route module passes
**37 tests, one skipped** (10.34 seconds), and the full focused Roads selection
passes **413 tests, one skipped** (38.10 seconds). The skip requires optional exact
converter integration configuration. `validation_environment_receipt.json`
retains source/log hashes, counts and exact helper snapshots; logs are under
`candidate_logs/`, distinct from the earlier aligned evidence.
