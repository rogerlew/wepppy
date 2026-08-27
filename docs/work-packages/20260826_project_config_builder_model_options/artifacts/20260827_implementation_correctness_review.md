# Implementation Correctness Review: Builder Model Options

**Reviewer**: independent correctness reviewer
**Date**: 2026-08-27 UTC
**Initial verdict**: Request changes

The initial review found no high-severity tuple-validation or serialization
defect. It requested stronger dependency diagnostics, reverse-transition UI
evidence, a genuine pre-binary manifest compatibility fixture, meaningful WEPP
model execution, and direct manifest-helper evidence.

The implementation was revised to:

- explain that a cleared selection is incompatible with the current
  combination rather than incorrectly blaming locale;
- dispatch the actual Multiple OFE change from `wepp_dcc52a6` and assert the
  visible `wepp_260803` auto-selection and submitted payload;
- load a static pre-binary schema-v1 Builder manifest/config using
  `wepp_dcc52a6`, then prove update preview is unavailable without migration;
- execute a real four-year hillslope fixture through both registered watershed
  and hillslope executable pairs and require return code zero plus WEPP's
  successful-completion marker; and
- inspect a materialized valid Builder manifest and a malformed manifest through
  the real helper.

**Final verdict**: Approved, conditional on Forest acceptance before exposure.

The reviewer confirmed that the prior findings are resolved and found no
remaining correctness blocker in backend validation, defaults, generated
config/manifest behavior, Preview derivation, or UI dependency clearing. The
Forest WBT Multiple OFE preparation/run remains mandatory before deployment or
exposure. A low residual evidence note remains: the static pre-binary manifest
is valid and proves legacy loading/update unavailability, but retaining a
complete historical artifact would strengthen literal historical fidelity.
