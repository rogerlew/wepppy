# Correctness review and artifact evidence

2026-11-21 UTC. Independent reviewer approved the native daily writer, cell adapter, retained diagnostics and staged NoDb publication. A second independent review covered the contract. Contract ancestors 8f42ac3fd and 86c00f07a precede the caller changes.

| Input or state | Expected and observed |
| --- | --- |
| Omitted raw forcing | Existing positional revision retains source tdew and writes the existing temperature log. |
| Valid warm, cool and midpoint-repaired days | Full daily weather columns and the four diagnostic columns agree with the former Python serializer. Signed-zero tie behavior is pinned. |
| Empty, shifted, short, long or reversed calendar | Native checks reject empty or unequal coverage and out-of-order labels. Scoped cases exercised shifted, short, long and reversed inputs. |
| Malformed month, nonfinite raw value or invalid derived weather | Explicit failure, with no completed revision marker. |
| Successful staged output | Real native NoDb test reloads mapping and reads matching published and retained CLI, CSV and ordering log. Raw parquet is preserved. |
| Revision failure following centroid commit | Existing failure tests verify the prior centroid remains available, no hillslope mapping is published and the retained attempt records failure. |
| Cell/nearest-cell generation | Actual CLIGEN file, daily dates, weather, diagnostic and quantization checks passed. |

The reviewer independently compared all numeric weather fields for a deterministic 366-day leap-year case with 76 floored days. No unresolved correctness finding. Existing run authorization, locking, job wiring and persistence contracts are untouched.

## Project replay

On forest, replayed production hillslope 142702 from diagonal-intersection in disposable local storage. Inputs were read-only copies of the centroid wepp.cli and prism800m-source-ws.parquet. The six monthly normal arrays came from the run's three retained revision rasters sampled at the stored watershed and hillslope centroids using get_monthlies. Compared against the actual retained production hillslope CLI and its dew-point CSV. Both files matched byte-for-byte across all 16,436 days. The native log counted 9,187 floored days. CLI SHA-256 was `2f8092cb3a33bff1d06cb021f43aea115fefbda8f518b0e5627f474834b95b26`.

Three interleaved local runs timed revision through final weather validation and diagnostic creation, with identical inputs. Native seconds were 0.0953, 0.0908 and 0.0920. Legacy native revision followed by the checkpoint Python floor took 0.9159, 0.8018 and 0.7998 seconds. This is a single-hillslope comparison. Queueing, tile sampling, fleet storage performance and retained-copy publication are outside the timer.

## Scoped validation

The paired Linux py312 release came from native task commit `771bdd6093a3581138af80adc56d97eb48deb095` and has SHA-256 `3c2bde80c363f6e216b4a14dc8365cb6cc165f13619937dc9c4f074dec7cc03a`. Native cargo tests passed 23. The five scoped pytest modules passed 111 tests in the isolated wctl runner, receipt `7d87023509e4429798d27770df8b1fc4/receipt.json`. They cover the native writer, cell adapter, PRISM build service, shared climate helpers, and staged revision success/failure. A first run exposed an unhydrated 2015 station-catalog LFS pointer in the task checkout. Restoring the tracked SQLite object fixed that fixture prerequisite. Scope ends at generated climate inputs and published run mappings. No fleet deployment, full watershed rebuild or WEPP model replay was requested.

The test-stub inventory passed. Runtime signature inspection confirmed the optional keyword and default on the native binding and NoDb facade agree with the facade stub. Module-wide stubtest stopped before comparison on mypy build errors in unchanged runtime_paths, SWAT and observed modules.
