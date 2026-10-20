# Water output interpretation and discovery

Status: Active. Started 2026-10-20 UTC.

## Purpose and scope

Correct the defects recorded in [the documentation audit](../../dev-notes/20261020_water_output_documentation_audit.md). Advanced users must be able to distinguish local OFE depths, physical hillslope water, threshold-filtered PASS delivery, and routed watershed flow. Publish an interpretation guide and variable reference, fix metadata and stale documentation, and connect Results, reports, and Usersum discovery.

Scientific behavior remains governed by the hillslope-water-aggregation contract and ADR-0099. No formulas, field names, dtypes, simulation defaults, authorization, or report calculations change. Historical vendor documents and closed packages remain immutable. Existing files do not acquire new scientific provenance when their README is regenerated.

## Authorization and complexity budget

The operator requested “scaffold and execute work-package to correct the defects” after the audit and previously authorized commit and push in this session. This package uses existing documentation, template, schema, and index tooling only: no dependency, service, datastore, or privilege additions. No production deployment.

Security impact: low (static documentation links and metadata only). No dedicated security review is required; independent correctness review will check prefix-safe links and unchanged access boundaries.

## Acceptance

A normal user can find water/PASS interpretation from Results and Usersum, search for latqcc/QOFE/SUBEVENT, and read area-weighted examples and field meanings without opening developer work packages. New native/Python metadata agrees. Generated run README retains bounded previews and explains version limitations. Rendered links and representative output artifacts pass focused checks; unrelated working-tree changes remain preserved.
