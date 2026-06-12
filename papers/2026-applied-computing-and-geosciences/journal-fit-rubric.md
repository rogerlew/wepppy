# Journal Fit Rubric — C&G vs. Applied Computing & Geosciences

> **DECIDED 2026-06-12: Applied Computing & Geosciences.** Retained as the record
> of the comparison; the C&G-first transfer-service strategy below is moot.

> Scored against the production-architecture thesis (see 00_planning.md).
> Sources: guide-for-authors.md (C&G, acquired 2026-06-12),
> applied-computing-and-geosciences.md (ACG, acquired 2026-06-12).
> Last updated 2026-06-12.

| Criterion | C&G | ACG | Advantage |
|---|---|---|---|
| Scope fit for architecture thesis | Conditional: dual-novelty bar; desk-rejects "software packaging or interface development"; redirects "applied implementation, software deployment, practical case studies" to ACG by name | Direct: scope list includes Distributed Systems, Software Engineering, E-Geoscience, Data Models, Computer Visualization, Geoinformatics, WWW | ACG |
| Thesis told straight? | No — requires distributed-computing research framing; DevOps/deployment vocabulary hazardous | Yes — production-platform story publishable as-is | ACG |
| Article type match | Original research article only | Research paper or Application article (real-world case study) | ACG |
| Novelty bar | "Original, high-impact research," substantive in both dimensions | "Scientifically and ethically sound"; completeness, depth, novelty, timeliness, quality, interest | ACG easier / C&G stronger signal |
| Desk-reject risk (this paper) | Material even with careful framing | Low | ACG |
| Word limit | 5,500 original (+10%), 6,500 revised; abstract/refs/captions excluded | 5,000 research & application articles; exclusions unstated (verify) | C&G slightly |
| Abstract / keywords | 300 w / 1–6 keywords / highlights required | 250 w / 1–7 keywords / highlights encouraged | tie |
| Software/repro gate | Public documented repo + reproducible examples mandatory at submission; closed-source desk-rejected | Research data Option C: deposit, cite, link (or explain) | tie for us (verify companion Rust repos for C&G) |
| Access model / cost | Hybrid; subscription route free; OA optional | Online-only, fully OA; mandatory APC (amount TBD — verify + check UI/USDA agreements) | C&G if budget-bound; ACG if OA required |
| Prestige / track record | Flagship since 1975; higher metrics | Launched 2019; metrics maturing (verify current) | C&G |
| Practitioner reach | Paywalled by default | OA — BAER teams/agencies/consultants hit no paywall | ACG for user community |
| Failure mode | Rejection → Article Transfer Service to ACG, no reformatting | No step-down path | C&G (graceful fallback) |

## Decision rule

- Production telemetry + benchmarks materialize → **C&G first** (distributed-computing
  framing); ACG via transfer service is the near-free fallback. Cost of the option:
  ~2–6 weeks.
- Telemetry audit comes back thin (plausible: Redis non-persistent, unstructured
  logs) → **ACG directly, Application article**, uncontorted framing, adoption +
  case-study evidence carries the paper.

The telemetry audit (00_planning.md, next steps #3) gates both drafting order and
venue selection.

## To verify before committing

- [ ] ACG APC amount; University of Idaho / USDA open-access agreements or waivers.
- [ ] ACG word-count exclusions (abstract/refs counted?).
- [ ] Current citation metrics for both (if relevant to co-authors).
