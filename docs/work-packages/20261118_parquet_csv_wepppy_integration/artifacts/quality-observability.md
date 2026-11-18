# Scoped quality checks

Broad-exception enforcement against M0 passed, net zero broad catches. New
ownership catches are documented boundaries and preserve cleanup/failure behavior.
Rust formatting, shell syntax and changed Markdown checks pass.

Observe-only quality telemetry: the download module shrank from 727 to 634 source
lines and its longest function from 125 to 105. The promoted supervisor grew from
258 to 308 source lines, longest function 61 to 85: request, child and cleanup
ownership remain in one conversion boundary to preserve auditable lifetime rules.
Two test modules cross the yellow file-size band through contract/lifecycle cases;
individual test-function lengths remain green. Radon was unavailable, so no
cyclomatic-complexity claim is made. No threshold is treated as a merge blocker.
