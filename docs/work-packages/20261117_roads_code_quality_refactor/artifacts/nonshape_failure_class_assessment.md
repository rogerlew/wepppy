# Non-shape v5 failure assessment

The completed v5 diagnostic contained 14 failed non-shape items and eight
PostgreSQL setup errors. A canonical isolated baseline run selected all 14 failed
items plus one representative setup error: **13 failed, one passed, one error**
in 17.48 seconds. The single pass was the latency case. Original failures and
baseline results remain retained; no failure is silently converted to a skip.

| Class | v5 count | Baseline evidence and disposition |
| --- | --- | --- |
| Ordinary deletion fixtures inherit managed `/wc1` storage | 4 failures | All four reproduce. Local test setup now clears retention ID/root only for ordinary temporary workspaces. Both complete modules pass: 50 passed in 15.61 seconds. |
| AF_UNIX pathname length | 1 failure | Reproduces with the long qualification basetemp before the hostile-socket assertion. A future complete module replay can use a shorter basetemp without source changes. |
| Missing generated `controllers-gl.js` | 1 failure | Baseline reproduces missing file. The ignored bundle exists in the primary checkout but is absent from both worktrees. No bundle or mount added here. |
| Incomplete profile-rendering fixture | 4 failures | All reproduce `account_display_email` undefined in Jinja. The isolated feature-access Flask fixture lacks the current profile template global. No unrelated fixture expansion made. |
| Missing Playwright modules | 3 failures | Both table-browser variants and the SQL-to-browser chain reproduce missing Node packages. Primary checkout dependencies exist; no dependency install or mount added here. |
| Catalog notification latency | 1 failure | V5 read-only p95 overhead was about 0.499 seconds against a 0.05-second threshold. Isolated baseline passes; full-suite load behavior remains inconclusive. No threshold change or repeated green-chasing. |
| PostgreSQL schema mismatch | 8 setup errors | All eight v5 errors lack `user.account_kind`; representative baseline setup reproduces the same error. No shared database schema or permissions changed. |

The bounded source corrections are three added lines each in
`test_batch_rq_retry_selection.py` and `test_project_rq_delete_run.py`: a comment
and two `monkeypatch.delenv` calls. The former change applies only to the ordinary
batch deletion test. The latter applies only to the shared ordinary deletion
helper. Dedicated retention cases configure their own storage and do not call
that helper. Production behavior and assertions remain unchanged. The full
50-item candidate result includes both dedicated retention cases.

`nonshape_failure_class_receipt.json` records the exact source transitions,
baseline equality for the other involved test modules, every baseline and
candidate JUnit outcome, and all eight schema error identities. The selection is
retained in `nonshape_baseline_selection.json`; exact commands and logs are under
`candidate_logs/`. These targeted runs support diagnosis and fixture validation;
the final collection observer must handle complete-module coverage replacement.

## Management sidecar source drift

The v5 source manifests differ only in
`wepppy/wepp/management/scripts/man42_5.man.json`. Its only semantic change adds
`_pmet_plant_names: null`, an existing parser default. The recursive import test
imports `export_covers.py`, which changes the process working directory to the
management scripts directory, and the unguarded
`data/UnDisturbed/dump_to_json.py`, which writes JSON for each `*.man` in that
directory. Running the writer on a copied input in isolated temporary storage
reproduced the observed changed bytes exactly, without modifying source.

Before restoration, the original and changed bytes and their diff were retained
under `management_sidecar_drift/`. At the integrator's direction, the file was
restored to exact HEAD bytes, which also match the immutable baseline and v5
source-before hash. `management_sidecar_drift_receipt.json` records hashes and the
successful copied-input reproduction. No runtime source correction was needed.
