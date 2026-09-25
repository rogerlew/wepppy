# Dead Horse Creek Daymet M3 audit

Status: closed, 2026-09-17 UTC. Started 2026-09-17 UTC.

## Purpose and scope

Audit the accepted Daymet M3 assessment for `thespian-cleanness`, compare its rainfall and probabilities with the preceding GridMET and synthetic PRISM assessments, and reassess the August 5–12, 2021 window identified by Rengers et al. (2024). Preserve closed audits as history.

Read-only scope: retained climate lineage, raster predictors, all saved result rows, normal authenticated report access, and published scientific interpretation. No climate rebuild, model run, deployment, parameter change, or project data mutation. Complexity budget: scripts and documentation only, using existing dependencies.

Security impact: low; existing authenticated read-only access. No new interfaces, permissions, or secrets. Dedicated security review not required. No production behavior change or parameterization ADR.

## Acceptance

Pin the accepted attempt and climate content; independently check spatial predictors, equations, units, event backlinks, frequency ranks, and published hashes. Establish actual Daymet lineage independently of the generic mode label. Compare the paper window without substituting dates. Verify browser report and downloads, retain limitations and preservation evidence, then close the plan and tracker.

## Deliverables

[Findings](artifacts/findings.md), reproducible audit scripts and machine-readable evidence, and [tracker](tracker.md).

## Closure

Numerical and authenticated browser checks pass; all 858 protected files and the accepted manifest remain unchanged. Daymet still has zero rain in the paper window. Confirmed source-parquet units defect and retained CLIGEN quality warning are documented in the findings, with bounded follow-up recommendations. Scientific event validation remains unestablished; closing this audit does not certify climate quality or repair those findings.
