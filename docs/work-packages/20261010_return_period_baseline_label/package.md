# Return-period baseline naming parity

Status: Closed 2026-10-10; implemented and live on forest. Bounded follow-up to the closed Omni comparison package.
User requests replacing Current project with verified GL dashboard labels.
Verified source: static/js/gl-dashboard/state.js (Undisturbed) and
layers/orchestrator.js (Burned after SBS detection). No dashboard changes.
Canonical contract: docs/ui-docs/contracts/return-period-omni-scenarios-contract.md,
Tables and CSV. Contract ancestor `450d3efd8`; implementation `bf0a97c37`. Only presentation
labels change. 35 targeted route/template tests passed; independent correctness
review approved. Authenticated browser verification of the actual forest report
and CSV returned 200 and labels Burned/undisturbed, with no page errors.
