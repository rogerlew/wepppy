# ENDUSER.md Authoring Guide

This guide defines how to write `ENDUSER.md` files for WEPPcloud and related usersum content.

Write for non-developers with backgrounds in hydrology, soil science, forestry, agriculture, range, watershed restoration, or land management. Assume roughly the knowledge level of an upper-division undergraduate hydrology student: readers should be comfortable with terms like runoff, infiltration, sediment yield, watershed, and soil texture, but they should not need to understand WEPPcloud internals, code structure, or queueing details.

## When to write an ENDUSER.md

Create an `ENDUSER.md` when a module, workflow, dataset, control, or output needs user-facing explanation beyond UI labels or terse parameter names.

Use `ENDUSER.md` for:

- workflow guidance,
- parameter interpretation,
- output interpretation,
- assumptions and limits that affect user decisions,
- domain context needed to use a feature correctly.

Do not use `ENDUSER.md` for:

- purely internal helper modules,
- queue wiring or deployment notes,
- developer architecture,
- low-level implementation details that do not change how a user works.

If the content should appear in usersum, publish it through `docs_manifest.yaml` and `nav_tree.yaml`. This guide is itself a developer-only usersum page because it defines the convention rather than serving end users directly.

## Core Audience Contract

Every `ENDUSER.md` should help a reader answer seven questions as quickly as possible:

1. What is this feature, file, setting, or output?
2. When should I use it?
3. What decisions does it affect?
4. What do I need before I start?
5. What happens when I change it?
6. How should I interpret the result?
7. What limits, assumptions, or uncertainty still matter?

Lead with those answers. Do not start with implementation history, code architecture, or theory-heavy background unless the reader needs that material to make a correct decision.

## Patterns Worth Reusing

Two hydrology-model documentation sites are especially useful models:

- [SWAT+ Documentation](https://swatplus.gitbook.io/io-docs) separates introduction, input files, output files, and theory. That separation helps readers move from overview to field-level reference without mixing purposes.
- [HEC-RAS Documentation](https://www.hec.usace.army.mil/confluence/rasdocs) splits user manuals, reference manuals, and application guides. The [Applications Guide introduction](https://www.hec.usace.army.mil/confluence/rasdocs/rasappguide/latest/introduction) explicitly frames examples around a problem statement, required data, solution steps, and output discussion.

Use the same discipline in `ENDUSER.md` files:

- keep overview, procedure, reference, and explanation visibly separated,
- show the user what problem the page solves,
- explain what inputs or data are needed,
- describe what outputs mean in decision terms,
- state current limitations instead of hiding them.

## Required Writing Rules

### 1. Lead with the user goal

Start with the management or modeling question, not the software internals.

Prefer:

- "Use this option when you want many plausible weather years instead of one observed sequence."
- "This table helps you interpret whether high sediment delivery is coming from hillslopes, channels, or both."

Avoid:

- "This route hydrates climate configuration state."
- "This module orchestrates parameter serialization."

### 2. Use plain language, then define technical terms

Specialized vocabulary is unavoidable in hydrology and soil science, but unexplained jargon is not.

- Define acronyms on first use.
- If the UI label is technical, keep the exact label and explain it in plain language immediately after.
- If a term has both a technical and everyday meaning, make the technical meaning explicit.
- If you must use a specialized term repeatedly, define it once and use it consistently.

Readers should not have to infer whether "delivery," "yield," "loss," "runoff," or "severity" has a technical meaning on a given page.

### 3. State units, scale, and scope every time they matter

End-user hydrology documentation becomes misleading very quickly when scope is vague.

Always tell the reader:

- the units,
- the spatial scale,
- the time scale,
- whether the value is observed, modeled, derived, defaulted, or user supplied.

Be explicit about distinctions such as:

- hillslope versus channel versus watershed outlet,
- event versus daily versus annual versus long-term average,
- sediment detached versus sediment delivered,
- measured data versus model estimate.

### 4. Explain why a parameter or output matters

Do not stop at a label definition.

For each important setting, answer:

- what it means,
- why the user would change it,
- what higher or lower values generally do,
- when the default is usually the right choice.

For each important output, answer:

- what is being reported,
- what a high or low value usually indicates,
- what common misreadings to avoid,
- when field validation or expert review is still needed.

### 5. Make procedures runnable

When the page tells the user to do something, make it executable as written.

- Use numbered steps for tasks.
- Use one action per step whenever possible.
- State where the action happens before the action.
- Tell the reader what they should expect to see next.
- Mark optional steps with `Optional:`.
- Prefer one best path over several equally weighted alternatives.

If a step depends on a decision, tell the reader how to choose.

### 6. State assumptions, limits, and uncertainty directly

Hydrology and erosion outputs are estimates, not guarantees.

Every `ENDUSER.md` that affects decisions should say, in user language:

- what assumptions the workflow makes,
- where the model or dataset is known to be stronger or weaker,
- what the output should not be used for by itself,
- when professional judgment, calibration, or field checks are still needed.

Avoid false precision, certainty theater, and blanket phrases such as "accurate" or "best" without context.

### 7. Keep pages scannable and accessible

- Use short paragraphs.
- Use descriptive headings.
- Prefer tables only when they reduce cognitive load.
- Use descriptive link text.
- Do not rely on color, screen position, or "see above/below" wording.
- If you add figures, captions should say what the reader should notice.

The first screen of the page should tell the reader what the page is for and when to use it.

## Recommended Page Template

Use this structure unless there is a strong reason not to:

```markdown
# [Feature, Workflow, Dataset, or Output Name]

One-sentence plain-language summary.

## What This Is For

## When to Use It

## Before You Begin

## Key Terms and Settings

## Steps

## Interpreting Results

## Assumptions and Limits

## Troubleshooting

## Related Docs
```

Some sections can be omitted when they do not fit the page, but `What This Is For`, `When to Use It`, and `Interpreting Results` should be treated as the default, not the exception.

## Recommended Table Patterns

For settings:

| Setting | What it means | Units or values | Why it matters |
| --- | --- | --- | --- |
| `Example setting` | Plain-language meaning | `mm/hr`, `true/false`, class names | What changes for the user |

For outputs:

| Output | What it represents | Units | How to interpret it |
| --- | --- | --- | --- |
| `Example output` | Physical or management meaning | `mm`, `kg/m^2`, `t/ha`, dimensionless | What high or low values usually suggest |

Do not create wide, dense tables that act like raw schemas. If a table needs more than four or five columns, split it or move detail into prose.

## Good and Bad Phrasing

Prefer language that connects the control to a decision.

Bad:

> The channel delineation threshold prunes low-order reaches using rasterized accumulation.

Better:

> The channel delineation threshold controls how much upslope area is needed before WEPPcloud maps a flow path as a channel. Higher thresholds usually produce fewer mapped channels.

Bad:

> Use stochastic climate for probabilistic analysis.

Better:

> Use stochastic climate when you want many plausible weather years rather than one observed sequence. This is useful for risk-style questions, such as how often runoff or erosion may exceed a threshold.

## What to Avoid

- dumping raw parameter names without interpretation,
- long theory sections before the user knows why the page matters,
- unexplained acronyms,
- internal class names, route names, queue names, or implementation details,
- saying "simply," "just," or other wording that hides complexity,
- mixing operator runbooks into end-user guidance,
- promising certainty where the model only provides an estimate.

## Review Checklist

Before publishing an `ENDUSER.md`, verify that:

- the first 150 words explain what the page is for and when to use it,
- all important acronyms and technical terms are defined on first use,
- every setting or output includes units and interpretation context,
- procedures tell the reader what result to expect after major steps,
- the page distinguishes modeled values from observed or uploaded values,
- assumptions, limits, and uncertainty are stated clearly,
- a hydrology undergraduate or land manager could paraphrase the page accurately,
- the page contains no unnecessary developer internals.

## Usersum Publication Rules

When an `ENDUSER.md` should appear in usersum:

1. Keep the markdown in normal repo form with relative `.md` links.
2. Add the document to `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`.
3. Add it to `wepppy/weppcloud/routes/usersum/nav_tree.yaml`.
4. Choose the lowest reasonable `min_role`. End-user docs should almost always be `user`.
5. Rebuild and validate the usersum index.

Relevant commands:

```bash
PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate
PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py build-index --write --require-vendor-files
wctl run-pytest tests/weppcloud/routes/test_usersum_docs_contracts.py tests/weppcloud/routes/test_usersum_docs_index.py --maxfail=1
```

Usersum rewrites in-repo markdown links. Keep links as normal `.md` links rather than hardcoding app routes.

## External References

These sources informed the guidance above:

- [SWAT+ Documentation](https://swatplus.gitbook.io/io-docs)
- [HEC-RAS Documentation](https://www.hec.usace.army.mil/confluence/rasdocs)
- [HEC-RAS Applications Guide: Introduction](https://www.hec.usace.army.mil/confluence/rasdocs/rasappguide/latest/introduction)
- [Google Developer Documentation Style Guide: Procedures](https://developers.google.com/style/procedures)
- [Google Developer Documentation Style Guide: Jargon](https://developers.google.com/style/jargon)
- [Google Developer Documentation Style Guide: Write for a global audience](https://developers.google.com/style/translation)
- [Google Developer Documentation Style Guide: Accessibility](https://developers.google.com/style/accessibility)
- [Microsoft Writing Style Guide: Scannable content](https://learn.microsoft.com/en-us/style-guide/scannable-content/)
- [Digital.gov Plain Language Guide: Test for understanding](https://digital.gov/guides/plain-language/test)
- [NOAA Office for Coastal Management: Seven Best Practices for Risk Communication](https://coast.noaa.gov/data/digitalcoast/pdf/risk-communication-best-practices.pdf)
- [AGU: Why a Plain Language Summary Matters](https://www.agu.org/Meetings/First-Timers-Guide/abstract-knowledge-center/Articles/Plain-Language-Summaries)
