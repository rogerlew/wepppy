# Onboarding audit selected corrections

Status: closed (code and focused validation), 2026-10-13; not deployed. Scope: operator-selected D01, D02, D13, D14, D18 from the primary onboarding audit. Other dispositions remain follow-up work.

D01 sets new AgFields projects to wepp_261010; D02 accepts readable SBS color tables with unknown colors left unassigned; D13 indefinitely defers ORCID documentation promotion; D14 directs internal-access requests to Mariana Dobre; D18 makes the FAQ official.

Security impact: low. The shared SBS admission condition changes, but authentication, upload caps, filesystem containment, native failure propagation and raster structural checks remain. Independent contract reviews cover correctness and security/noninterference. Complexity budget: no new dependencies, services, schemas, queue edges, or production deployment.

Acceptance: direct native raster admission/classification/export/remapping evidence, regression coverage, literal config readback, consistent user documentation and updated audit dispositions. Existing persisted executable selections and known SBS classifications stay unchanged. No claim of AgFields scientific parity across binaries is implied by the requested default edit.

Completed after checkpoint `b4be200b4`: 182 focused tests passed, one skipped; config readback, docs/catalog validation and independent correctness/security reviews pass. See [validation](artifacts/validation.md) and [tracker](tracker.md). Other 13 audit dispositions remain open.
