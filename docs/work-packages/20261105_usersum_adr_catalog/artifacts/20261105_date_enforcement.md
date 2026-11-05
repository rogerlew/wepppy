# ADR date enforcement

## Failure and scope

47 of 138 populated numbered ADRs had decision dates only in prose or no explicit
Date field. The template had the field, but generic Markdown lint did not enforce
it. Catalog discovery remained complete; those records sorted last as undated.
The operator requested hardening after the verified metadata backfill.

Enforce explicit valid dates for the same direct numbered files read by the
catalog. Missing/placeholder/impossible dates, Review Date-only records and
body-only dates fail with an actionable filename. Preserve recognized legacy
plain/bold/inline Date syntax. The README/template are not decision records and
are excluded. Empty/missing source roots fail the checker so a wrong working
path cannot report success. No web behavior or role boundary changes.

## Failure-class coverage

| Consumer | Finding and repair | Validation |
| --- | --- | --- |
| ADR template and authors | Placeholder copied or date omitted; add local instructions and template reminder | Copy template unchanged must fail; filled Date must pass |
| Generic Markdown lint | Valid Markdown is not valid ADR metadata; retain lint and add specific checker | Missing and invalid Date fixture failures |
| Docs Quality CI | No ADR-specific gate; add checker to source spec and regenerate workflow | Generator parity and exact CLI run |
| Usersum catalog | Correctly sorted missing dates last; reuse its parser, no runtime edit | Checker accepts all supported date forms and all 138 current records |

Search boundary: ADR source/authoring guidance, existing catalog, documentation
quality workflow source/generated artifact and repository check tooling. No
managed pre-commit hook configuration exists; provide a local pre-commit command
without installing hooks. No external dependency, privileged CI job or service.

## Validation

- Test-first check failed before the checker existed; retained log at
  `/tmp/usersum-adr-date-check-red.log`.
- `wctl run-pytest tests/tools/test_check_adr_dates.py tests/weppcloud/routes/test_usersum_bp.py tests/weppcloud/test_usersum_template_wiring.py --maxfail=1`:
  **122 passed**, 4 existing dependency warnings, 18.69 seconds.
- CLI tests run an isolated interpreter (`-I`) from a different directory, so
  passing does not depend on installed application packages or `PYTHONPATH`.
- `python3 -I tools/check_adr_dates.py`: all **138 ADRs** pass.
- Workflow generation and `--check` pass through `wctl exec weppcloud python
  scripts/build_forest_workflows.py`; only source/generated Docs Quality files
  changed. The host Python lacks PyYAML, so the existing container runtime was
  used; no dependency installed. The generator's existing missing nightly-table
  notice is unchanged and does not affect this gate.
- The generated job runs the checker as an ordinary failing step before generic
  lint/tooling verification. Trigger paths cover ADR Markdown, checker, shared
  parser and checker tests. No `continue-on-error` or fallback success is added.
- CI execution on the remote runner is not claimed; source/generated parity and
  the exact command are validated locally.
- Full broad native suites are not repeated for this bounded tooling follow-up;
  earlier package attempts and their incomplete outcomes remain documented.

Independent read-only correctness review by `/root/adr_contract_correctness`:
PASS, no findings. Reviewer independently ran `python3 -I -S -B tools/check_adr_dates.py` against all 138 records, confirmed missing-root exit 1,
and checked workflow generation. Hosted CI execution and historical accuracy of
the previously audited backfill were outside this bounded review.

Final documentation lint passes for README, template, ADR instructions, test
instructions and package docs. `git diff --check` passes.
