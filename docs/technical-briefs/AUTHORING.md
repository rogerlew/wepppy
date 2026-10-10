# Technical Brief Authoring Guide

## Audience and Scope

Write for hydrologists, soil scientists and users interpreting model results.
Start with the practical decision, not the investigation chronology. Aim for
four to six pages; add detail only when it changes interpretation. Use a dated
brief ID, change date, document date/revision and explicit publication status.

Required first-page fields: Roger Lew, University of Idaho,
`rogerlew@uidaho.edu`, plus an accurate AI authoring disclosure. Verify these
defaults for each brief. Approval of a model or parameter change is not approval
of the new document. Do not imply independent peer review or institutional
endorsement from an owner's publication decision.

## Required Content

1. What changed: before/after values with units, affected classes, mapping scope,
   exact software/data identity and exclusions.
2. Why: the scientific or operational rationale, alternatives and why the
   smallest defensible correction was selected.
3. What to expect: representative magnitudes, frequency, event-level behavior
   and unchanged controls, not only aggregate fit.
4. What to do: new versus existing projects, regeneration, override precedence,
   compatibility and whether any automatic migration occurs.
5. Limits and evidence: what was actually tested, assumptions, untested
   conditions and links to the decision, preserved studies and current guidance.

Keep calculated quantities, assumptions and observations separate. Distinguish
runoff from routed discharge, hillslope delivery from outlet sediment, and
input values from evolving model state. Rankings support interpretation;
they are not proof of observational accuracy or universal acceptance gates.
Do not describe a consistency correction as accepting a degradation merely
because a model output decreases. Report consequential changes nonetheless.

Use plain language first, then only the equations and implementation details
needed to explain consequences. Distinguish parameter changes from model-code
changes. Avoid a full historical diary or a new implementation campaign.

## Evidence and Disclosure

Pin change and evidence identities. Preserve output units, rounding, climate
period, baseline and build provenance. A new brief may reuse retained evidence;
do not imply new simulations were run. Do not require uncommitted resources
to compile a brief or to pass a publication check.

Detailed descriptions of legacy WEPP algorithms are allowed. Clearly attributed
original explanatory code is allowed. Raw legacy source, mixed-origin diffs and
source attachments require separate authorization; NSERL has not agreed to
public release of WEPP source. Do not copy those into the public static tree.
Neither model agreement nor successful compilation establishes scientific
accuracy, accessibility certification or disclosure permission.

## Build and Review

Copy the template into a dated topic directory and keep each brief self-contained.
Fill in metadata, content, references and manifest. Tailor the AI disclosure.
Build with standard TeX Live packages and shell escape disabled:

```bash
mkdir -p build
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
pdftotext -layout build/main.pdf build/main.txt
```

Repeat if references change. Check logs, selectable text, links, page layout,
units and numeric anchors against retained evidence. Inspect all rendered pages.
Keep review records outside static. Approval is explicit and document-specific.
At publication, remove draft labels, freeze revision/hash and copy exactly those
bytes and the public manifest to the destination in the series README.
