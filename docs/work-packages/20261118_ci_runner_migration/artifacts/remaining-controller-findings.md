# Controller findings exposed by restored execution

Source candidate: 97a82588310dc91a9e3dd2b11547200db0a6dd3a.
Local browser outcome: 16 passed, two failed, zero skipped. Retained evidence:
controller-final.json, controller-final.log.gz and the two compressed page snapshots.
These are unresolved assertion failures, not proven preexisting production defects;
a before/after baseline comparison has not been performed. The migration preserves
both tests and their failure status.

- Features Export: `prepareFeaturesExport` attempts to select a layer on a newly
  created project without generated export inputs. The browser reports that the
  checkbox did not change state. Follow-up should establish the smallest valid
  project/catalog fixture before changing the expectation; retain unavailable-layer
  behavior and authorization.
- PATH Cost-Effective: the injected error's message is rendered, but its second
  detail line is absent. Follow-up should compare the HTTP error adapter and shared
  stacktrace contract against `docs/schemas/rq-response-contract.md`, with a focused
  regression test. Do not remove the detail-line assertion to make CI green.

Accessibility's automated suite passes its existing acceptance rules, not a claim
of full WCAG conformance. The retained report still records two serious axe findings
(link-in-text-block and nested-interactive) and Theme Metrics reports 59 non-enforced
contrast findings. The migration changes no accessibility thresholds or exceptions.

Full pytest coverage and the broad baseline are deferred until after integration
in accordance with the operator's earlier instruction. Their cancellation records
are separate from successful focused checks; no full-suite pass is claimed.
