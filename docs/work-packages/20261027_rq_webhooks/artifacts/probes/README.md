# Disposable webhook acceptance probes

These are local acceptance tools, not deployment entry points. Use the installed
`wctl` with `-f docs/work-packages/20261027_rq_webhooks/artifacts/probes/https-compose.yml`.
All writable project data and private fixture credentials live under the ignored
`.pytest_cache/webhook-workflows` and `.pytest_cache/webhook-tls` directories.
Never use these scripts against shared Redis or original projects.

## Boundary tests

`run_container_tests.py` starts a private host Redis Unix socket and runs container
pytest through `wctl`. It supplies both RQ and catalog fixture socket variables,
verifies the disposable marker, and terminates only its own Redis process. Example:

```sh
.venv/bin/python docs/work-packages/20261027_rq_webhooks/artifacts/probes/run_container_tests.py tests/rq/test_webhook_tracking.py tests/microservices/test_rq_engine_webhooks.py -q
```

`restart_restore_probe.py` uses the same ownership pattern plus filesystem barriers
around a real RDB save/restart. The container holds an admission reservation while
the host restarts Redis. It asserts no publication and no stale-armed delivery.

## API, model and receiver fixture

1. `setup_workflow.py` creates owned directories, a private JWT key and the copied
   culvert inputs. It refuses to overwrite an existing fixture. Source project and
   base-project mounts in Compose are read-only.
2. Create a short-lived local test CA/certificate with `subjectAltName=DNS:webhook.test`
   under `.pytest_cache/webhook-tls`; retain its private key only there. The isolated
   receiver uses this certificate; only fixture clients set `SSL_CERT_FILE` to it.
3. Start fixture Redis and receiver. Append `RQ_WEBHOOK_REDIS_RUN_ID` with that
   Redis process's `INFO server` run_id to the private runtime environment. This
   deliberately arms only the disposable instance; a restart requires review/rearm.
4. Run `prepare_model_copies.py` using the driver. It copies the retained continuous
   model source, rebases NoDb paths with the canonical fork helper and invalidates
   copied catalog identity under explicitly configured managed roots.
5. Start API, default worker pool, batch worker and dispatcher, then run
   `workflow_probe.py`. Run `workflow_readback.py` after its three submissions
   complete. The readback compares exact inputs/raw outputs, path-normalized logs,
   typed parquet schemas and exact row multisets, then exact receiver/event bytes.
6. For mixed culvert inputs run `prepare_culvert_mixed.py`, then
   `culvert_workflow_probe.py` and `culvert_readback.py`. The fixture explicitly selects a two-year local
   stochastic climate template; it changes no production defaults. Cached raster
   inputs are copied from the source batch. One original point is retained and 35
   are deliberately moved outside their watersheds to exercise caught failures.
7. Run `backlog_performance.py` after model work stops. It measures 1,000 actual
   worker transitions per group, with 80 hung TLS events and four 5,000-member
   evaluation roots in the tracked group. It requires four active senders and actual
   receiver traffic during timing, then asserts both approved overhead limits.
   Earlier zero-attempt artifacts are explicitly limited to evaluator pressure.
8. Stop/remove this Compose project with `wctl -f … down`. Remove only its ignored
   private fixture directories after retaining sanitized evidence.

The receiver/dispatcher remain on an internal network with a public-classified
fixture address; no external receiver is contacted. The batch worker also has
ordinary model-data egress for its USDA soil request. The fixture uses UID 1000,
GID 993, umask 022 and the production development image/mount conventions.

Final acceptance uses six default and four batch workers, matching the canonical
development Compose configuration. `workflow_probe.py` records and verifies those
counts; timing refuses to begin while model workers are busy. Early one-slot batch
isolation and failed fixtures remain diagnostics. The final parallel mixed-culvert
case passed with one model success and 35 caught domain failures.

Intermediate diagnostics retain their actual failure states. Only successful final
readback artifacts constitute output/delivery acceptance; an accepted submission
or finished root alone is insufficient. No script retains bearer/browse tokens.
