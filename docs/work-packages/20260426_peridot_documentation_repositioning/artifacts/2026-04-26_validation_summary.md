# Peridot Documentation Repositioning Validation Summary (2026-04-26)

## Scope Validated

Repositories:

- `/home/workdir/peridot`
- `/workdir/wepppy`

Validation covers documentation changes only. No runtime behavior was changed.

## Commands

### WEPPpy Doc Lint

Command:

```bash
cd /workdir/wepppy
wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning
```

Result: pass.

Output:

```text
✅ 7 files validated, 0 errors, 0 warnings
```

### Peridot Markdown/Doc Tooling Check

Peridot does not currently expose repository-local markdown/doc tooling.

Discovery commands:

```bash
cd /home/workdir/peridot
find . -maxdepth 3 \( -path './target' -o -path './.git' \) -prune -o -type f \( -path './tests/*' -o -name '*.sh' -o -name 'Makefile' -o -name 'Justfile' -o -name '.markdown*' -o -name '*lint*' \) -print | sort
rg --files -g '*.md' -g 'Cargo.toml' -g '!target' | sort
```

Result: no Markdown/doc linter config or command was found. Manual link/path validation was used.

### Additional Changed WEPPpy Docs Lint

Command:

```bash
cd /workdir/wepppy
wctl doc-lint --path wepppy/README.md --path docs/culvert-at-risk-integration/dev-package/README.md --path docs/dev-notes/data_tables_standardization.spec.md --path docs/dev-notes/query_engine.spec.md --path docs/projects/i-crews/st_joe/procurement-request.md --path docs/schemas/output-scope-contract.md --path docs/standards/dependency-evaluation-standard.md
```

First result: failed on a pre-existing broken link in `wepppy/README.md` to missing `../API_REFERENCE.md`.
The dead link was removed because `wepppy/README.md` was already touched by this package.

Final result: pass.

Output:

```text
✅ 7 files validated, 0 errors, 0 warnings
```

## Manual Link and Path Validation

Peridot documentation paths expected to exist:

- `/home/workdir/peridot/README.md`
- `/home/workdir/peridot/docs/contracts/watershed-output-contract.md`
- `/home/workdir/peridot/docs/benchmarks.md`
- `/home/workdir/peridot/docs/migration/prepwepp-to-peridot.md`
- `/home/workdir/peridot/docs/operations.md`
- `/home/workdir/peridot/sub_fields_abstraction.spec.md`
- `/home/workdir/peridot/dev-notes.md`

Validation command:

```bash
cd /home/workdir/peridot
set -e
for f in \
  README.md \
  docs/contracts/watershed-output-contract.md \
  docs/benchmarks.md \
  docs/migration/prepwepp-to-peridot.md \
  docs/operations.md \
  sub_fields_abstraction.spec.md \
  dev-notes.md; do
  test -f "$f"
  printf 'ok %s\n' "$f"
done
```

Result: pass.

Output:

```text
ok README.md
ok docs/contracts/watershed-output-contract.md
ok docs/benchmarks.md
ok docs/migration/prepwepp-to-peridot.md
ok docs/operations.md
ok sub_fields_abstraction.spec.md
ok dev-notes.md
```

Local Markdown link target validation also passed for README and new docs:

```text
ok README.md -> docs/contracts/watershed-output-contract.md
ok README.md -> docs/benchmarks.md
ok README.md -> docs/migration/prepwepp-to-peridot.md
ok README.md -> docs/operations.md
ok README.md -> sub_fields_abstraction.spec.md
ok README.md -> dev-notes.md
ok docs/migration/prepwepp-to-peridot.md -> ../contracts/watershed-output-contract.md
ok docs/migration/prepwepp-to-peridot.md -> ../benchmarks.md
ok docs/migration/prepwepp-to-peridot.md -> ../operations.md
```

## Runtime Test Scope

No runtime tests were required because this package is documentation-only. Peridot runtime source was read to validate documented behavior, but binaries and algorithms were not modified.

Spelling-normalization preview using `uk2us` on changed WEPPpy package docs produced no diff.

## Residual Gaps

- Peridot watershed CLI error propagation remains a runtime follow-up.
- `field_flowpaths.csv` duplicate `topaz_id` header remains a schema follow-up.
- Numeric speedup claims remain hypothesis-level until tied to benchmark artifacts.

## Post-Review Remediation Validation

Review remediation artifact:

- `docs/work-packages/20260426_peridot_documentation_repositioning/artifacts/2026-04-26_review_remediation.md`

Rerun result after review remediation: pass.

Commands:

```bash
cd /workdir/wepppy
wctl doc-lint --path PROJECT_TRACKER.md --path docs/work-packages/20260426_peridot_documentation_repositioning
wctl doc-lint --path docs/culvert-at-risk-integration/weppcloud-integration.plan.md
```

Output:

```text
✅ 8 files validated, 0 errors, 0 warnings
✅ 1 files validated, 0 errors, 0 warnings
```

Peridot manual path and local-link validation was rerun after review remediation and passed.
