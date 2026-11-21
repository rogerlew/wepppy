# Native PRISM hillslope dew point

## Purpose

Generate final hillslope weather directly in the native daily writer and retain verifiable weather and diagnostic artifacts. Work in the WEPPpy and wepppyo3 task checkouts.

## Progress

- [x] Trace the existing build and specify the keyword and generated output contract.
- [ ] Commit the reviewed contract.
- [ ] Implement native derivation and connect the PRISM Multiple caller.
- [ ] Build the extension and compare real CLI and diagnostic outputs using scoped tests.

## Surprises & Discoveries

The Python replacement rewrites numeric precision across the whole daily row. Preserve that behavior for this mode and compare all fields.

## Decision Log

Use dated arrays in the optional keyword so same-length shifted calendars fail. Compute against the repaired, serialized Tmin. Keep diagnostics and validation in the native path.

## Execution and validation

Extend cli_revision/src/lib.rs in wepppyo3. Pass dated forcing through the existing climate_observed_build and climate_build_helpers thread pool in WEPPpy. Use an isolated extension build. Exercise native weather readback, unused-option compatibility and scoped NoDb tests. Staging and finalize preserve the prior climate on failures. Reverting the caller restores the Python path with the compatible native extension.

## Outcomes & Retrospective

Implementation pending.
