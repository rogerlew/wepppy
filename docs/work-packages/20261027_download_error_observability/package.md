# Download error observability

Status: implementation, focused/platform validation and broad assessment complete; one unrelated Roads provenance blocker retained. Fix meaningful server-to-client failure reporting without changing
project access or successful delivery. See the [ExecPlan](prompts/active/implementation_execplan.md).

Security impact: high (public error responses). Dedicated security review required.
Complexity budget: existing services and libraries only; no new infrastructure.
Acceptance: safe actionable configuration errors, correlated unexpected errors,
client-visible HTTP details, nonzero failure exits and successful-byte parity.

The user required this on 2026-10-27 after bare HTTP 500 responses prolonged
download diagnosis. Root cause repair alone does not satisfy observability.

Hypothesis: safe classified responses plus client propagation reduce an injected
configuration failure to one actionable terminal message and log lookup. Health
signals and recurrence triggers are in the canonical web-runtime contract's
Download failure diagnostics section. No temporary callus or scheduled monitoring
is introduced. General unknown exceptions retain a safe message and reference;
known authored messages remain explicit. Deployment remains separate.

See [coverage matrix](artifacts/failure_class_matrix.md) and
[validation](artifacts/validation.md). Independent correctness and security
reviews are retained; secondary QA also passes. Broad coverage and its unrelated provenance blocker are recorded in validation; all remaining cases completed.

Incident precedent: wepp1 browse `aria2c.spec`, 2026-10-26 16:31:10 PDT, raised `SECRET_KEY (or SECRET_KEY_FILE) must be configured` through lazy Flask owner lookup. The earlier secret-dependency audit repaired provisioning; this package repairs the missing response/client observability contract.
