# Current-project second attempt: complete initialization

Preserve `current-project-v1` and its failed workflow. All 66 hillslope native
calls and its watershed completed, followed by a loss-grid export failure because
`wepp/plots` was absent. This is a harness initialization omission, not evidence
of native failure or a reason to disable configured export.

Use a fresh `current-project-v2` copy of the same immutable source. Before model
preparation, preserve all copied directories targeted by `Wepp.clean`, then call
the actual canonical initialization: `ensure_bootstrap_main`, `clean`, baseflow
and phosphorus map checks (see `wepp_rq.run_wepp_rq`). Complete hillslope and
watershed preparation follows, with unchanged settings except the declared
experimental r7 binary selection. Freeze all inputs, NoDb/config/code identities,
service identity and exact matched binaries before any new native invocation.

Preserve the first attempt's reviewed runtime flags, 66 hills/193 OFEs, 16-year
calendars and separate source-material scope. Require native logs and the standard
hillslope interchange boundary before watershed execution. Retain configured
export behavior and installed reports; do not bypass the failed postprocessing
stage or label partial execution a successful workflow. Keep the original source,
withheld split, parameter defaults and human UI gate unchanged. This repeat is a
bounded harness recovery, with no production or model-source changes.

Execution remains the bounded public-controller lane declared in v1. It is not
RQ pipeline parity: the queued MOFE path skips loss-grid generation, while
`Wepp.run_watershed` performs it when configured export is enabled. Keep that
public method's behavior and exercise its configured output instead of hiding
the failed stage. RQ also has TC cleanup, return-period TSV and query-catalog
stages beyond this lane. Do not claim those consumers, queue/browser acceptance
or catalog availability from the controller result. Roads validation will use
the existing disposable-controller suite and its own explicit accounting gates.
