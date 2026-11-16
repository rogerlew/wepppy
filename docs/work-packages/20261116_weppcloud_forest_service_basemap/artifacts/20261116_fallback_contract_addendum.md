# FSBASE-02 fallback navigation addendum

Starting revision: `277d55fba`, with FSBASE-01 implementation in the working tree.
This addendum precedes only the navigation repair below, not the already
checkpointed basemap implementation.

Real Flask fallback rendering fails with BuildError for `weppcloud_site.about`.
The existing mocked-url_for template test did not expose it. The operator was
asked whether to replace that broken link with “WEPPcloud user guide” pointing
to the existing guide, and explicitly answered “Replace with user guide” on
2026-11-16. Existing package checkpoint commit authority remains in effect.

Canonical amendment: FSBASE-02 in
`docs/ui-docs/contracts/forest-service-basemap-contract.md`. Exact source scope:
`wepppy/weppcloud/templates/landing.htm` and
`wepppy/weppcloud/templates/header/_global_header_fixed.htm`, the only two
confirmed consumers of the deleted endpoint. Replace the endpoint/label with
`usersum.view_markdown`, category `weppcloud`, filename `user-guide.md`.
No route, auth, scientific, state, or other navigation change. Security impact
of this addendum is low: same-origin public documentation navigation only.

Compatibility: fallback and legacy header regain rendering; the defunct About
link is replaced by the operator-selected existing guide. Test real Flask URL
building for both consumers plus rendered fallback/browser keyboard disclosure.
The feature's existing valid-state/input matrices continue to apply.

Independent read-only contract reviews: `/root/contract_correctness` and
`/root/contract_security` both passed FSBASE-02 on 2026-11-16 with no findings. Commit this accepted addendum
before editing either navigation link. Final correctness/security implementation
reviews remain separate.
