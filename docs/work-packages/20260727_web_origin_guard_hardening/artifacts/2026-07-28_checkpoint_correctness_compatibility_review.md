# REM-04 checkpoint correctness and compatibility review

## Review scope

Independent, read-only review of the GOV-00A-M1D / REM-04 WP00 checkpoint
candidate for contract completeness, cross-service behavioral parity,
compatibility, executable test vectors, and internal consistency.

Evidence reviewed:

- `docs/schemas/weppcloud-csrf-contract.md`
- `docs/ui-docs/diagnostics-page.spec.md`
- the REM-04 contract decision, bounded-remediation decision, package, tracker,
  ExecPlan, and WP01-WP04 prompts
- the three current same-origin implementations and their focused tests
- the browser-state reset implementation/configuration and focused tests
- the diagnostics check definitions, report builder, and focused tests

No contract, governance, production, or test file was changed by this review.

## Findings

### Medium C-01: forwarded-origin policy is internally contradictory

**Evidence**

The new Browser Same-Origin Guard Contract says raw forwarded headers MUST NOT
independently add allowed origins and says the rq-engine legacy
`RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` switch MUST no longer expand the
guard after REM-04. Later in the same canonical document, under
“rq-engine and 3rd-Party API Requirements,” the contract says forwarded-origin
aliases MUST remain opt-in through that exact switch.

The existing rq-engine suite has an explicit
`test_session_token_cookie_path_can_opt_in_to_forwarded_origin_aliases` that
expects those raw values to authorize an otherwise disallowed origin. WP01
would therefore be required both to remove and preserve the behavior, and WP04
has no unambiguous expected result for this compatibility case.

**Required action**

Choose one normative post-REM-04 rule and make every section, WP prompt, and
test-vector expectation agree. If the switch is retired for this guard, state
whether the environment variable remains accepted but inert or is removed,
and explicitly require replacement/removal of the existing opt-in test. If
some forwarded values remain usable, define the trusted middleware boundary
that normalizes them before the guard and make clear that the raw-header
compatibility switch itself cannot authorize an origin.

### Medium C-02: the upstream-TLS bridge is not specified as an executable tuple rule

**Evidence**

The canonical order permits an HTTPS browser Origin to bridge an internally
observed HTTP request only when host and “effective public port” agree, but it
does not define how each of Flask, rq-engine, and query-engine obtains that
public port when the application request tuple is `http://host:80`. The
contract decision instead says host and effective public port must “agree,”
without identifying the comparison tuple.

WP04 then describes the bearhive vector as
`Sec-Fetch-Site: same-origin` plus `X-Forwarded-Proto: http` and an HTTPS
Origin, expecting acceptance. That raw header is expressly non-authoritative
under the candidate contract and, by itself, does not establish an internal
HTTP request scheme in all three framework test clients. The ExecPlan describes
the topology in terms of the internal request scheme, which is materially
different from WP04's header-only recipe.

The no-Origin case is clear: `Sec-Fetch-Site: same-origin` authorizes it. The
present-HTTPS-Origin case is not: an implementation cannot determine from the
candidate whether acceptance requires a configured public HTTPS origin,
proxy-normalized request properties, same host with scheme-default port 443,
or another explicit bridge tuple.

**Required action**

Define the bridge as an exact input/output algorithm for both cases:

1. `same-origin` with no Origin; and
2. `same-origin` with a present public HTTPS Origin while the authoritative
   application request tuple is internal HTTP.

Name the authoritative public-origin source and comparison ports for each
framework. Replace WP04's raw `X-Forwarded-Proto: http` recipe with framework-
specific fixture setup that actually produces the intended authoritative
request/public-origin tuples. Add negative vectors proving that the same raw
header cannot create an allowed origin and that scheme bridging is unavailable
without the required trusted/configured public tuple.

### Medium C-03: the “fixed check catalog” omits the normative title/severity mapping

**Evidence**

Diagnostics specification section 9 requires copied title and severity to come
from a fixed report catalog, not runtime results, but the purported catalog
lists only fourteen IDs. It provides no normative title or severity for any
ID. Those values currently live across four JavaScript registration modules,
so copying them from runtime definitions would preserve the mutable input path
that the new boundary is intended to eliminate.

The contract decision says the “complete fixed catalog” is normative in
section 9, but the catalog is not complete enough to implement or test. WP03
likewise asks for a fixed catalog without supplying the missing mapping.

**Required action**

Add a normative table containing the exact `id`, copied `title`, and copied
`severity` for every allowed check. State whether catalog registration is a
single immutable report-layer constant or whether trusted module definitions
may populate it; if the latter, define the trust and duplicate-ID rules.
Require tests that inject a known ID with hostile runtime title/severity and
prove the fixed values are copied.

### Medium C-04: WP04 overstates cross-surface CSRF parity and lacks a realizable harness contract

**Evidence**

The canonical endpoint matrix says query-engine bearer calls do not require
CSRF, while the three guarded surfaces have different outer controls:
Flask reset is covered by Flask-WTF, rq-engine's cookie route uses session
authentication plus its origin guard, and query-engine bandwidth mutations use
the origin guard without Flask-WTF. The canonical guard text correctly says
existing CSRF/auth remains layered outside the predicate.

WP04 nevertheless calls the deliverable a “CSRF-enabled same-origin/header test
matrix across all three surfaces,” asks for an “absent token” expectation for
each surface, and says to initialize `CSRFProtect` “where the surface enforces
CSRF” without enumerating which matrix assertions apply to which adapter. It
also names the Flask reset suite while its objective says “valid same-origin
token,” but does not specify how that test obtains a real Flask-WTF token after
initializing the extension. A single shared expected-status matrix cannot
directly encode the distinct outer-layer outcomes.

**Required action**

Split WP04's executable model into:

- one shared pure origin-decision vector set consumed by all three guards; and
- explicit per-surface outer-layer vectors: valid/missing/invalid Flask-WTF
  token for Flask only, cookie/session authentication for rq-engine, and the
  existing query-engine boundary controls.

Define the Flask token acquisition fixture and expected error precedence when
both CSRF and origin evidence are invalid. Remove any implication that rq-engine
or query-engine must gain Flask-style CSRF, and require parity assertions on
the predicate decision rather than identical final HTTP status where outer
layers differ.

### Low C-05: exact cookie ownership is clear, but default/fallback provenance should be testable

**Evidence**

The cookie contract precisely limits deletion to configured session and
remember names, paths, and domains, normalizes an unset path to `/`, and forbids
synthetic variants and generic CSRF names. It says remember domain falls back
to session domain “only where the authentication configuration itself does
so,” but does not cite or define the configuration/default rule that decides
this. This wording could lead implementations to introduce an ad hoc fallback
that differs from Flask-Login's effective cookie behavior.

**Required action**

Name the effective Flask/Flask-Login configuration rule used for the remember
tuple, or state that only the resolved `REMEMBER_COOKIE_DOMAIN` value is used.
Include unset-domain and differing session/remember-domain vectors in the
complete tuple test. This may be resolved directly or explicitly accepted by
the package owner if the implementation already exposes one canonical
effective-value helper.

## Compatibility and parity assessment

The candidate makes the missing-signal behavior explicit and consistent:
missing `Sec-Fetch-Site`, Origin, and Referer rejects on all three guards. It
also correctly preserves the distinction between the same-origin predicate and
existing CSRF/authentication layers. Exact cookie name/path/domain ownership
and the prohibition on generic CSRF/parent-domain deletion are substantially
complete.

However, the forwarded-header contradiction and under-specified present-Origin
upstream-TLS bridge prevent a deterministic cross-service implementation. The
incomplete copied-report catalog and WP04 harness ambiguity prevent the stated
regression evidence from being implemented without inventing contract choices.

## Finding counts

- Unresolved high: **0**
- Unresolved medium: **4**
- Unresolved low: **1**

## Verdict

**FAIL — checkpoint not ready to seal.**

Resolve all four medium findings, disposition the low finding, and repeat this
independent correctness/compatibility review after the material contract
changes.

## Post-Fix Rereview — 2026-07-28

### Scope

Rechecked the current canonical CSRF/session contracts, diagnostics
specification, contract decision, review disposition, package acceptance
criteria, and WP01-WP04 execution prompts against C-01 through C-05. No file
other than this review artifact was edited.

### Finding closure

#### C-01 remains unresolved — Medium

The canonical session contract and the new Browser Same-Origin Guard section
now correctly make `RQ_ENGINE_TRUST_FORWARDED_ORIGIN_HEADERS` accepted but
inert. However, the same canonical CSRF contract still says under
“rq-engine and 3rd-Party API Requirements” that forwarded-origin aliases
“MUST remain opt-in” through that switch. This is the exact contradiction
reported in C-01.

The disposition's statement that the contracts are reconciled is therefore
factually premature. Remove or replace the stale normative bullet so every
canonical section delegates to the inert-switch rule.

#### C-02 remains unresolved — Medium

The canonical contract now defines authoritative service inputs and an exact
same-host HTTP:80 application tuple to HTTPS:443 Origin bridge. WP04 also now
uses authoritative request fixtures and includes raw-header negative vectors;
those changes resolve the algorithm and WP04 concerns.

WP01 still supplies a conflicting “Contract (normative intent)” and validation
recipe. It permits an absent-signal “documented default” instead of the
canonical mandatory rejection, treats `cross-origin` as equivalent to the
canonical `cross-site` Fetch Metadata value without defining unknown-value
behavior, omits the exact HTTP:80-to-HTTPS:443 bridge, and still instructs the
implementer to simulate upstream TLS with raw
`X-Forwarded-Proto: http`. Because WP01 executes before WP04 and calls this
text normative, it can produce an implementation contrary to the reviewed
canonical algorithm.

Replace WP01's duplicated contract and validation recipe with an explicit
reference to the canonical decision order and authoritative tuple fixture.

#### C-03 closed

Diagnostics section 9 now supplies the immutable fourteen-entry
ID/title/severity catalog, fixed status messages, duplicate and unknown-ID
behavior, sanitized/recomputed report metadata, and hostile-input test
requirements. This is deterministic and executable.

#### C-04 partially resolved but remains unresolved — Medium

WP04 now correctly separates the shared predicate vectors from Flask-WTF,
rq-engine cookie/session authentication, and query-engine boundary controls.
It defines real Flask token acquisition and CSRF-first error precedence.

The package-level acceptance criterion still requires “valid token” and
“absent token” coverage “on all three surfaces.” That contradicts WP04 and the
canonical statement that rq-engine and query-engine do not gain Flask-style
CSRF. Amend the package criterion to require CSRF-token vectors only on Flask
and the shared origin vectors plus each service's existing outer control on
the other surfaces.

#### C-05 remains unresolved — Medium

The canonical cookie contract now clearly says reset owns only the resolved
session and remember tuples, uses resolved configuration directly, never
invents a remember-domain fallback, and tests unset and distinct domains.

WP02 still repeatedly defines success as deleting a WEPPcloud-owned CSRF
cookie, directs the implementer to preserve one if “genuinely owned,” and
requires manual confirmation that the session/remember/CSRF cookies are
removed. This contradicts the canonical determination that Flask-WTF state is
stored in the session and that generic CSRF cookie names are not owned. The
execution prompt could therefore reintroduce the deletion that REM-04 is meant
to remove.

Revise WP02's objective, instructions, deliverables, and manual check to name
exactly the session and remember tuples and to state that Flask-WTF CSRF state
is cleared through session deletion only.

### New-issue check

No additional high-severity issue was found. The stale package/prompt
statements above are treated as continued manifestations of C-01, C-02, C-04,
and C-05 rather than new findings.

### Remaining counts

- Unresolved high: **0**
- Unresolved medium: **4**
- Unresolved low: **0**

### Post-fix verdict

**FAIL — checkpoint still not ready to seal.**

C-03 is closed. C-01, C-02, C-04, and C-05 require the specified consistency
edits, followed by another post-fix rereview. The review disposition must not
record them as accepted-fixed until the contradictory canonical and execution
text is actually removed.

## Final Rereview Confirmation — 2026-07-28

### Verification

The four remaining inconsistencies identified in the first post-fix rereview
are corrected:

- **C-01 closed.** The stale rq-engine bullet in the canonical CSRF contract
  now states that raw forwarded-origin aliases cannot authorize the cookie
  path and that the legacy switch is accepted but inert. This agrees with the
  Browser Same-Origin Guard section, session contract, contract decision,
  disposition, and required negative regression.
- **C-02 closed.** WP01 now delegates normative authority to the canonical
  guard contract, explicitly requires missing-signal rejection and the sole
  same-host HTTP:80-to-HTTPS:443 bridge, and models the upstream-TLS case
  through the authoritative request tuple. Raw forwarded headers are required
  negative vectors rather than topology authority.
- **C-04 closed.** Package acceptance now separates the shared predicate
  matrix across all three guards from Flask-only token vectors, rq-engine
  cookie/session authentication, and query-engine boundary controls. It agrees
  with the executable WP04 harness.
- **C-05 closed.** WP02 now limits ownership and deletion to the resolved
  session and remember tuples, explicitly removes both generic CSRF names, and
  treats Flask-WTF state as session-contained in its objective, instructions,
  and manual validation.

C-03 remains closed. No new high, medium, or low correctness/compatibility
finding was identified in the corrected checkpoint candidate.

### Final remaining counts

- Unresolved high: **0**
- Unresolved medium: **0**
- Unresolved low: **0**

### Final verdict

**PASS — correctness/compatibility checkpoint review complete.**

The REM-04 checkpoint candidate is internally consistent and sufficiently
specific for WP01-WP04 implementation and regression validation. This verdict
does not itself make the checkpoint authoritative; the separate security
rereview, disposition update, standalone documentation-only commit, and
recorded ancestor requirements still apply.
