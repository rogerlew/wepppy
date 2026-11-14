# Omni baseline eligibility

Status: accepted by operator on 2026-11-13. Documentation scope; runtime
enforcement is not established by this change.

## Supported baseline

Omni Scenarios must start from an undisturbed or burned project baseline with
no applied treatments. A baseline already modified by the Treatments module,
including thinning, mulch, or prescribed fire, is unsupported. Assigning
treatment land-cover classes directly does not make that project an eligible
baseline either. This restriction concerns
applied treatments, not merely having the Treatments module enabled.

Define treatments as Omni scenarios. Thinning and prescribed fire use an
undisturbed context; mulch uses a burned base scenario. For a burned project,
include an Omni `undisturbed` scenario when needed by thinning or prescribed
fire. These supported scenario dependencies do not authorize starting Omni
from an already treated project.

## Existing treated projects

Start from an untreated project or a saved pretreatment copy, rebuild and
verify its landuse, soils, and WEPP baseline outputs, then create Omni scenarios.
Removing a module or clearing treatment selections is not evidence that earlier
changes to assignments or generated inputs have been undone. An `undisturbed`
scenario removes fire effects; it is not a general treatment-reset workflow.

## Rationale and scope

The baseline establishes the undisturbed or burned reference condition for
comparison. Applying Omni alternatives on top of prior baseline treatments
mixes treatment histories and obscures what the comparison represents. Support
for cumulative baseline-treatment-plus-Omni workflows is deliberately excluded;
do not infer support from an execution path that happens to accept the inputs.

This decision does not disable MOFE projects or supported Omni treatment
scenarios, change soil coefficients, or certify the existing treatment execution
paths. It adds no automatic rejection, cleanup, or recovery behavior.
