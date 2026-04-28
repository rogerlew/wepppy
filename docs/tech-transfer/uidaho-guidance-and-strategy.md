# UIDaho Tech Transfer Guidance and Strategy

## Status

- Updated: 2026-04-28
- Scope: WEPP.cloud stack and related repositories
- Purpose: simple operating guidance aligned to minimum disclosure duty and low-friction delivery
- Legal posture: operational guidance only, not legal advice

## Operating Posture

- Meet minimum disclosure duty.
- Keep development and support moving.
- Do not pursue patents by default.
- Use disclosure primarily to secure organizational and state support.
- Default to open/public engineering unless sponsor terms require confidentiality.

## Core Anchors

- UI policy requires disclosure of potentially protectable discoveries developed in UI research/program context: [FSH 5300](https://www.uidaho.edu/policies/fsh/5/5300).
- UI guidance states faculty/staff/students are required to disclose potentially protectable IP developed using university resources: [UI IP policy overview](https://www.uidaho.edu/research/business-industry-partnerships/intellectual-property-policy).
- OTT service workflow identifies invention disclosure as the first step and supports advising/NDA/MTA coordination: [OTT request assistance](https://support.uidaho.edu/TDClient/40/Portal/Requests/ServiceDet?ID=789).

## Explicit Non-Goals

- No active patent-mining campaign.
- No claim-locking effort that slows delivery.
- No broad trade-secret program for core platform engineering.
- No release freeze waiting on patent strategy.

## Minimum Duty Checklist

For work that may be UI-owned or sponsor-encumbered:

1. Submit disclosure to OTT.
2. Include enough facts for compliance and ownership review:
   - what was built
   - who built it
   - when it was built
   - funding/sponsor context
   - where it is documented or deployed
3. Identify any known public disclosures (repo, docs, talks, demos).
4. Flag any sponsor or third-party confidentiality constraints.

If federal funding applies, route reporting through institutional channels (OTT/OSP) rather than ad hoc project handling.

## Low-Friction Workflow

1. Batch disclosures as umbrella updates (for example monthly or per milestone), not per commit.
2. Use one short inventory covering major technical deltas across the stack.
3. Include this explicit instruction in each disclosure:
   - "No patent pursuit requested at this time. Public-release/open-source-first posture preferred unless sponsor requirements override."
4. Continue development/support immediately after submission.
5. If OTT wants follow-up detail, provide only scoped addenda.

## Publication and Release Defaults

- Public repo/docs releases remain the default operating model.
- Do not publish sponsor-confidential or third-party-confidential details.
- For potentially novel items, disclose first when feasible, then continue normal publication cadence.
- No expectation of long-term secrecy for routine platform engineering.

## Support-First Objective

Use disclosures to request concrete support, not patent overhead:

- staffing capacity (engineering, operations, documentation)
- state/agency partnership support
- procurement and contracting support
- hosting/operations sustainability support
- legal/admin clarity for open deployment and service models

## Priority Areas to Disclose (Current)

- Git-backed run-input workflow with scoped JWT auth, path-normalized verification, and pre-receive scientific file validation.
- Run-scoped NoDb architecture with file-backed singleton state, Redis cache tiers, and lock discipline.
- Hybrid async reliability model (status stream + polling fallback + structured error contracts).
- Native geospatial/model substrate deltas in `wepppyo3`, `peridot`, and `weppcloud-wbt` where changes are materially novel.

## One-Page Disclosure Template

Use this structure for each umbrella submission:

1. Objective: compliance disclosure and support request.
2. Requested posture: no patent pursuit, open/public by default.
3. Delta summary: 3-10 bullets of material technical changes.
4. Contributors and affiliations.
5. Funding/sponsor context.
6. Existing public disclosures.
7. Confidentiality constraints (if any).
8. Specific support requested from UI/OTT/state partners.

## Escalation Triggers

Escalate immediately to OTT/OSP/OGC only when one of these is true:

- explicit sponsor requirement for confidentiality or patent election
- external NDA/MTA terms that restrict publication
- export-control or controlled-data concerns
- ownership dispute across institutions or private entities
- direct commercialization negotiation requiring formal license terms

Outside these cases, continue the low-friction disclosure cadence.

## Working Rule

Disclose enough to satisfy duty and unlock support. Do not let patent strategy dominate engineering operations.
