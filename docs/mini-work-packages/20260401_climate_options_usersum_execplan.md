# ExecPlan: Author Climate Options End-User Documentation and Wire Climate Control Description Link

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md` and is scoped as an ad hoc mini work package under `docs/mini-work-packages/`.

## Purpose / Big Picture

WEPPcloud users need a complete, plain-language explanation of Climate Options that maps directly to what they see in the Climate panel and what the backend actually does. After this change, users will have a dedicated Usersum page that explains every climate option, station selection mode, spatial mode, and advanced option with practical guidance on when to use each choice, and the Climate panel will include a built-in description with a link to this page.

## Progress

- [x] (2026-04-01 05:01Z) Completed discovery: loaded root + local AGENTS guidance, ExecPlan template, climate UI template/controller, and NoDb climate catalog/build/scaling code.
- [x] (2026-04-01 05:01Z) Created this ExecPlan at `docs/mini-work-packages/20260401_climate_options_usersum_execplan.md`.
- [x] (2026-04-01 05:03Z) Defined a reusable climate-mode section template and delegated mode-by-mode/subsection drafting to parallel subagents.
- [x] (2026-04-01 05:07Z) Authored `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md` by consolidating subagent findings into one end-user guide with required file-spec links.
- [x] (2026-04-01 05:07Z) Added Climate Options description block + usersum link in `wepppy/weppcloud/templates/controls/climate_pure.htm` using the RAP-style control-shell description pattern.
- [x] (2026-04-01 05:08Z) Ran validation (`wctl doc-lint --path ...`) and finalized this ExecPlan with outcomes and revision notes.

## Surprises & Discoveries

- Observation: `climate-options.md` does not currently exist in Usersum; the Climate control has no dedicated description block.
  Evidence: repository search found no `climate-options.md` path; `climate_pure.htm` currently invokes `ui.control_shell(...)` without a `description=` argument.
- Observation: Spatial mode `MultipleInterpolated` is constrained to observed Daymet/GridMET modes only.
  Evidence: `wepppy/nodb/core/climate_mode_build_services.py` raises `ValueError` when mode is not `ObservedPRISM` or `GridMetPRISM`.
- Observation: AU heuristic station mode has backend endpoint support but is not currently exposed by shipped dataset metadata (`station_modes`) in standard Climate Options datasets.
  Evidence: mode `3` endpoint exists in `climate_bp.py` and service method exists in `climate_station_catalog_service.py`, while current `climate_catalog.py` entries do not advertise `3` in standard exposed datasets.

## Decision Log

- Decision: Use source-of-truth behavior from `wepppy/nodb/locales/climate_catalog.py`, `wepppy/nodb/core/climate*.py`, and `wepppy/climates/cligen/cligen.py` as the basis for user documentation claims.
  Rationale: Requested page must explain suitability, data provenance, and availability accurately; UI labels alone are insufficient.
  Date/Author: 2026-04-01 / Codex.
- Decision: Delegate climate-mode subsections and context-heavy subsections to parallel subagents, then centrally reconcile into one coherent end-user doc.
  Rationale: User explicitly requested subagent dispatch and thorough per-mode investigation.
  Date/Author: 2026-04-01 / Codex.
- Decision: Document region/system-managed hidden catalog options (`observed_db`, `future_db`, `agdc`) in a dedicated section so end users understand availability differences by interface/context.
  Rationale: The request asked for each climate option plus availability context; hidden options still materially affect operator-facing behavior.
  Date/Author: 2026-04-01 / Codex.
- Decision: Present user-provided spatial guidance (PNW calibration and micro-climate recommendation for Multiple Interpolated) as practical guidance, not hard-coded rule.
  Rationale: Maintains clear separation between code-enforced constraints and empirical operator guidance.
  Date/Author: 2026-04-01 / Codex.

## Outcomes & Retrospective

The requested documentation and UI-linking scope was completed end-to-end. A new comprehensive usersum guide now exists at `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`, covering each climate dataset option, station mode behavior/availability, CLIGEN `.par` and observed `.prn` usage, spatial mode guidance (including PRISM revision behavior), and all Climate Advanced Options with practical use guidance.

The Climate Options control now includes a description block with a direct usersum link to the new guide in `wepppy/weppcloud/templates/controls/climate_pure.htm`, following the same interaction pattern used by RAP and other modernized controls.

Validation completed successfully:

- `wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md` -> pass
- `wctl doc-lint --path docs/mini-work-packages/20260401_climate_options_usersum_execplan.md` -> pass

## Context and Orientation

The Climate control UI lives in `wepppy/weppcloud/templates/controls/climate_pure.htm` and is wired by `wepppy/weppcloud/controllers_js/climate.js`. Dataset options, locale constraints, station-mode availability, and supported spatial modes are defined in `wepppy/nodb/locales/climate_catalog.py` and enforced in `wepppy/nodb/core/climate_input_parser.py` plus `wepppy/nodb/core/climate_mode_build_services.py`.

Station-mode behavior and option-list endpoints are implemented in `wepppy/weppcloud/routes/nodb_api/climate_bp.py` and NoDb station selection services in `wepppy/nodb/core/climate_station_catalog_service.py`.

Observed-climate `.prn` processing and CLIGEN `.par` usage are implemented in `wepppy/climates/cligen/cligen.py` (`df_to_prn`, `Prn`, `Station`, `Cligen.run_observed`) and climate build helpers in `wepppy/nodb/core/climate_build_helpers.py`.

Usersum destination documentation path is `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`.

## Plan of Work

Author this change in four passes. First, define a strict climate-mode section template so mode writeups are consistent (purpose, data source, geography/time availability, station/spatial compatibility, recommended use, cautions). Second, dispatch subagents for each climate mode plus separate subagents for station modes, spatial modes/PRISM revision behavior, and advanced options to produce source-grounded draft bullets. Third, compose and edit `climate-options.md` into a coherent non-developer guide including requested guidance and required links to input file specs. Fourth, add a description block to `climate_pure.htm` in the same style as RAP control descriptions, linking to the new usersum doc.

## Concrete Steps

From `/workdir/wepppy`:

1. Create and maintain this ExecPlan while implementing.
2. Spawn parallel subagents with mode/template assignments and source-file constraints.
3. Write `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`.
4. Edit `wepppy/weppcloud/templates/controls/climate_pure.htm` to include a description block with `usersum_doc_link('weppcloud', 'climate-options.md', ...)`.
5. Run:
   - `wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`
   - `wctl doc-lint --path docs/mini-work-packages/20260401_climate_options_usersum_execplan.md`
6. Update this ExecPlan with final outcomes and revision note.

## Validation and Acceptance

Acceptance requires:

- `climate-options.md` exists and explains:
  - each climate option with suitability, data used, and where data is available,
  - station selection modes and where they are available,
  - what CLIGEN does and how `.par` files are used,
  - how observed mode uses `.prn` files,
  - spatial modes guidance including Single/Multiple/MultipleInterpolated and PRISM revision routine,
  - each Advanced Option with function, purpose, and recommended use cases,
  - links to `../input-file-specifications/cligenparms.md` and `../input-file-specifications/climate-file.spec.md`.
- `climate_pure.htm` contains a Climate Options description block with a usersum doc link.
- `wctl doc-lint` passes for the new/edited docs.

## Idempotence and Recovery

Edits are additive and safe to rerun. Re-running doc lint is idempotent. If a draft section is inaccurate, revise the markdown directly and re-run lint.

## Artifacts and Notes

Key artifacts to produce:

- `docs/mini-work-packages/20260401_climate_options_usersum_execplan.md`
- `wepppy/weppcloud/routes/usersum/weppcloud/climate-options.md`
- `wepppy/weppcloud/templates/controls/climate_pure.htm`

## Interfaces and Dependencies

No new dependencies are required. This work relies on existing Usersum rendering and existing Jinja helper `usersum_doc_link` for the control description link.

Revision note (2026-04-01 05:01Z, Codex): Created and activated this mini work-package ExecPlan before implementation, with explicit source-of-truth files, acceptance criteria, and validation commands.
Revision note (2026-04-01 05:08Z, Codex): Marked implementation complete after subagent-assisted drafting, usersum authoring, climate control description-link wiring, and successful doc-lint validation.
