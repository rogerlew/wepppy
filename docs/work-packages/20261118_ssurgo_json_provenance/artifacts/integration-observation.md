# Remote integration observation

Observed 2026-11-18 at 02:18 UTC; receipts were freshly fetched and verified.
WEPPpy PR #674 merged accepted db0764445a333575ade8a3a3d4c2e8e589ee1ec1 into
master at 2efc849f33b032418235f948be5c4c1e3ac5641d. The merge tree is identical
to the accepted PR head. Both required governance checks passed, as did remote
stubtest and documentation checks. Baseline tests and artifact observability were
still pending at this observation; the check snapshot preserves that distinction.
The accepted checkout passed all 75 focused soil tests with real disposable Redis.

Service PR #1 merged accepted 92272042e3b8f8450b8a0d3a5875ea9bda4bda96 into
main at 37b1e92f6fc84c95cd5109977b212b0c3104c41b. Its local main was fast-forwarded.
The shared dirty WEPPpy master checkout was not changed. No deployment was performed.

Original PR #673 was closed because its branch inherited unrelated protected work.
The original source history remains intact. The replacement copied only the four
soil commits onto remote master; original numerical evidence and source identity
checks are documented in validation.md. No policy approval or bypass was used.

These post-subject receipts are retained on audit/ssurgo-json-integration-20261118;
they are audit evidence, not additional unmerged implementation. Their claims are
remote ancestry observations, not production-release approval.
