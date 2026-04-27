# CLIGEN Observed Runtime Contract

This note captures the WEPPpy caller contract for CLIGEN observed input mode
(`-O <prn> -t6 -I2`).

## Process Contract

`Cligen.run_observed` runs CLIGEN with:

- per-attempt timeout: `20` seconds
- timeout retries: `3`
- retry backoff: exponential base `0.5` seconds, capped at `5.0` seconds, with
  jitter

Timeouts are treated as flake candidates only while retries remain. A timeout
attempt is terminated, any partial `.cli` is removed, and the next attempt starts
from a clean output path. If all attempts time out, `run_observed` raises
`TimeoutError`.

If CLIGEN exits non-zero, `run_observed` removes any partial `.cli` and raises
`RuntimeError`. A non-empty `.cli` is accepted only after CLIGEN exits with
status `0`.

## Rationale

The `intriguing-kingmaker:p980` incident showed that a short observed CLIGEN
timeout can leave a non-empty but truncated `.cli`. The run ended at
`22 May 1981` because WEPPpy killed CLIGEN after 5 seconds and then accepted the
partial output. The wrapper must not treat non-empty output as success after a
timeout or non-zero exit.

CLIGEN itself is responsible for returning a clean status at the end of valid
observed input. WEPPpy is responsible for process supervision and for ensuring
partial products from killed or failed attempts cannot be mistaken for valid
climate files.
