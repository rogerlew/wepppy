# Add 7777 single-file soils

Maintain this plan under docs/prompt_templates/codex_exec_plans.md.

## Purpose and context

Allow opted-in users to upload one7777 soil and apply it to every hillslope and
OFE. wepppy/wepp/single_input.py validates input; the preserving writer in
wepppy/wepp/soils/utils/wepp_soil_util.py writes native fields. NoDb preparation
already opts uploaded soils into this writer and owned synthesis repeats profiles.

## Progress

- [x] Traced native and owned parser layouts.
- [x] Independently reviewed canonical contract committed as e3a12ba42.
- [x] Implemented validator/writer/help and regression coverage.
- [x] Focused205 and regression305 tests passed; native1/2/12/32OFE passed.
- [x] Exact supplied-file authenticated upload/build/download and archive/restore passed.
- [ ] Finish broad suite and independent reviews, then close.

## Surprises & Discoveries

7777 has ten layer fields and profile anisotropy; numeric comparisons against
7778 currently incorrectly group it with the six-field2006 layout.

## Decision Log

2026-09-28: preserve7777 without migration because supplied hydraulics are user
inputs. Reuse existing admission, source publication, synthesis and worker paths.

## Plan of Work

First commit contract and independent reviews. Then explicitly distinguish7777
in validator and preserving serializer, extend existing soil-format and native
artifact test matrices with a sentinel fixture, and update UI/user/developer
guidance. Finally run focused tests and broad regression, inspect actual prepared
files and native outputs, and obtain independent correctness/security reviews.

## Concrete Steps and Acceptance

From repository root use wctl run-pytest tests/wepp/test_single_input_soil_formats.py
tests/nodb/test_single_input_sources.py tests/nodb/test_single_input_artifacts.py.
Extend native test matrix to7777 at1/2/12/32OFEs and modifiers at1/3OFEs. Inspect
all ten layer values and profile anisotropy, source immutability and nonempty native
loss outputs. Run wctl run-pytest tests --maxfail=1; doc-lint changed docs.

## Compatibility and Recovery

Add accepted version without changing schemas or default serializer. Tests use
temporary paths; source archives remain opaque. Revert code only with uploaded
7777 projects preserved and compatible processing restored. No deployment here.

## Outcomes & Retrospective

7777 is implemented and wired through existing upload/preparation paths. Focused
artifact/native tests and live disposable-run acceptance pass. Broad regression
and final review closure remain pending. No deployment performed.
