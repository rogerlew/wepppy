# Visibility consumer audit

2026-11-05 UTC. Starting revision `9cd9efb467`. Broken assumption: controller existence implies activation. Canonical authority: registry **Runtime Semantics**, feature-access-governance-contract FA-01/FA-02, shared controller **Singleton + bootstrap**. No normative delta.

| Consumer | Evidence and disposition | Regression plan |
| --- | --- | --- |
| Observed run context | Confirmed: Ron always initializes state; off/empty renders shell | enabled × preview × absent/initialized/empty-results/populated |
| Observed page/bootstrap fallback | Must preserve retained-results inspection in both templates | real template render and bootstrap JSON |
| Observed bootstrap hasResults | Confirmed: Jinja None.results is Undefined, which is not None | None versus results None/{} |
| Observed bootstrap selection | Confirmed: unconditional controller construction when off | execute rendered selection in Node |
| Observed singleton | Confirmed: stale form/delegates after first enable/replacement; enabled empty form hidden | Jest absent/enable/replacement/click once |
| WEPP completion notification | Indirectly constructs Observed before enable; keep notification interface and make absent form a no-op | absent completion, later bootstrap; preserve retained visibility |
| Debris Flow | Source-audited: apparently similar visibility predicate is protected by mod-gated load | existing role/render tests |
| Ash, Omni, Roads, Geneva, RUSLE | Source-audited: predicates explicitly require own mod; no same-class confirmed defect | existing scoped render/bootstrap tests |
| RAP, OpenET, Treatments, AgFields, Features Export, DSS Export, PATH-CE, postfire debris flow | Source-audited: own mod checks precede visible state | existing scoped render/bootstrap tests |
| Rangeland Cover, RHEM, SBS | Source-audited: template/flags use mod membership; no same-class confirmed defect | existing scoped template coverage |
| Omni Contrasts | Source-audited: own id, prerequisite and inspection checks | existing visibility matrix |
| DSS Export bootstrap | Unconditional selection, but existing bootstrap refreshes DOM; no confirmed stale binding defect | source precedent only; no whole-module validation claim |
| Culvert/Batch | Explicit standalone registry exclusions, no run-page section | existing registry tests |
| Project dynamic module handler | Calls Observed bootstrap on current context after section insertion | exercise Observed replacement, retain Project suite |

Scope is the run-page registry, non-registry optional sections, paired initial/dynamic bootstrap, and WEPP completion caller. Source-audited peers are not claims of runtime completeness. No loader, initialization, action authorization or scientific-output changes. Tests already reproduce enabled-empty hiding, absent-form network probe and retained-result hiding after completion; Python missing-state and selection regressions precede implementation. Security triage remains none. Malformed serialized state remains the existing NoDb loader's responsibility; this patch adds no parsing or persistence boundary.
