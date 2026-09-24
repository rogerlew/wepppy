# Pubroot tooling and publication preparation

## Local installation

Installed in the repository `.venv` on 2026-09-21:

```bash
.venv/bin/python -m pip install --only-binary=:all: pubroot==0.1.0
.venv/bin/pubroot --help
.venv/bin/pubroot topics --journal earth --json
```

The package is a local editorial tool, not a WEPPcloud runtime dependency.
No production requirements, agent rules, or global skills were added. Installation,
CLI help, and a read-only taxonomy request succeeded. No article was submitted.

## Scoped dependency assessment

No Pubroot precedent was found in the dependency registry or inspected project
configuration. Its publication/search CLI does not replace an owned modeling
component; critical-path performance benchmarking is not applicable.

PyPI metadata on the installation date reports version 0.1.0, released
2026-02-18, Python >=3.7, no declared dependencies, one published release, and
no listed vulnerabilities. The empty vulnerability list is not a security audit.
The listed maintainer is `buildngrowsv`; funding, maintainer redundancy, and a
stable API history were not established. The wheel is pure Python. Its SHA-256 is
`97bfe440e3904b9c28dd2601ac528b3e07b25db1312724714adba6bcf19e39fd`.
Submissions depend on GitHub CLI and Pubroot's GitHub workflow; Markdown drafts
remain portable. Source inspection established a release/website compatibility
gap below, so installation is not evidence of submission readiness.

## Working submission metadata

| Field | Working value |
| --- | --- |
| Article Title | OMNI: Interactive watershed treatment assessment with spatial contrasts and scenario analytics |
| Category | `earth/sustainability` |
| Submission Type | Case Study |
| Supporting repository | `https://github.com/rogerlew/wepppy` |
| Commit SHA | Select the evaluated release when evidence is complete |
| Authors | To be confirmed; do not infer scientific authorship from the submitter account |
| Abstract and Article Body | Finalize from [paper.md](paper.md) |

## Installed CLI compatibility limitation

The PyPI 0.1.0 CLI lacks `guide` and a submission dry-run option. Its `submit`
implementation accepts only top-level journal slugs and emits an older issue
layout. The current upstream issue form expects `journal/topic` categories and
specific `###` field headers. Do not use the installed `submit` command for this
manuscript without first resolving and verifying that mismatch.

At submission time, use the current official issue form or a reviewed current
CLI version. Follow the current parser/form rather than the older website's
frontmatter example. Inside Article Body, use `##` section headings: the current
agent guide reserves `###` headings for issue-form fields. The manuscript scaffold
uses `##` sections and keeps submission metadata here to avoid premature coupling
to the outdated installed parser.

## Preparation checklist

- [ ] Complete the [evidence checklist](evidence.md) and remove all drafting notes.
- [ ] Confirm venue, authorship, disclosure, and publication authorization.
- [ ] Recheck taxonomy, issue-form fields, and parser/CLI compatibility.
- [ ] Pin the evaluated source commit and retain the corresponding run artifacts.
- [ ] Host figures at durable absolute HTTPS URLs tied to the reviewed artifacts.
- [ ] Review the final article and exact submission fields locally.

Submitting creates a public GitHub issue and may lead to automatic publication.
The present task authorizes installation and a local scaffold, not submission.
Pubroot attributes platform submissions to the GitHub account opening the issue;
scientific coauthor names belong explicitly in the manuscript.

## Sources checked

- [PyPI package](https://pypi.org/project/pubroot/)
- [Taxonomy](https://pubroot.com/journals.json)
- [Editorial guidelines](https://pubroot.com/editorial-guidelines/)
- [Current agent submission guide](https://github.com/buildngrowsv/pubroot-website/blob/main/_cli/AGENT_SUBMISSION_GUIDE.md)
- [Current issue form](https://github.com/buildngrowsv/pubroot-website/blob/main/.github/ISSUE_TEMPLATE/submission.yml)

These are mutable upstream references; recheck and pin relevant versions before
submission. No review-speed, acceptance, or scientific-validation guarantee is
inferred from installation or platform marketing.
