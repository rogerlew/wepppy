# ENDUSER Stub Authoring Guide

This guide defines lightweight end-user stub documents for WEPPcloud usersum pages.

Use a stub doc when the topic is narrow and practical: where files live, how to prepare an input, what a small group of artifacts means, or how to avoid a common mistake. Write for non-developers with backgrounds in hydrology, soil science, forestry, rangeland, watershed restoration, or land management. Assume roughly the knowledge level of an upper-division undergraduate hydrology student.

## When to use a stub doc

Use a lightweight stub when the page:

- answers one narrow question,
- can usually stay under about 300 to 900 words,
- mainly orients the reader to files, inputs, outputs, or a short procedure,
- does not need a full feature walkthrough or a detailed settings discussion.

Good stub topics:

- run directory layout,
- where to find common outputs,
- how to prepare an upload,
- what a short list of files is for.

Do not use a stub when the page needs to explain:

- a full module or workflow,
- multiple settings with tradeoffs,
- output interpretation in depth,
- substantial assumptions, limits, or uncertainty.

For those cases, use the [ENDUSER.md Authoring Guide](enduser-authoring-guide.md).

## Core Audience Contract

A stub doc should let the reader answer four questions quickly:

1. What is this page for?
2. When do I need it?
3. What are the few files, rules, or steps that matter most?
4. What common mistake should I avoid?

If the page needs much more than that, it probably is not a stub anymore.

## Common Stub Types

### Locator stubs

Use for "where is it?" topics such as run directories, `.nodb` files, GeoJSON files, or common Parquet outputs.

Lead with:

- what the artifact family is for,
- which files users most often look for,
- which files are optional or interface-specific.

### Preparation stubs

Use for "how do I make this uploadable?" topics such as soil burn severity rasters.

Lead with:

- what WEPPcloud expects,
- the safest recommended workflow,
- the most common validation failures.

### Interpretation stubs

Use for small artifact groups where users need a quick orientation but not a full model explanation.

Lead with:

- what the artifact represents,
- what scale it applies to,
- what it should not be confused with.

## Required Writing Rules

### 1. Put the answer first

The first paragraph should solve the reader's main question. Do not start with implementation history or architecture.

### 2. Keep scope narrow

A stub should stay focused on one task or one artifact family. If you need several major sections with separate decisions, split the page or promote it to a full end-user guide.

### 3. Prefer short tables over long prose

Stub docs work best when the reader can scan:

- a checklist,
- a short file-location table,
- a short validation-message table,
- a short "do this, not that" table.

### 4. Say when files or folders are optional

WEPPcloud runs are heterogeneous. If a directory appears only after a build step, only in some interfaces, or only when a mod is active, say so directly.

### 5. Keep developer internals out

Do not include class names, queue jobs, route names, cache layers, or implementation fallbacks unless they change what the user should do.

### 6. Link outward instead of expanding sideways

If the topic touches a larger workflow, link to the fuller document instead of absorbing that content into the stub.

## Recommended Stub Template

Use this structure unless a simpler layout is clearer:

```markdown
# [Topic Name]

One-sentence summary.

## What This Page Helps You Do

## What To Look For
or
## What WEPPcloud Expects
or
## Key Files and Folders

## Recommended Workflow
or
## Common Files
or
## Common Validation Messages

## Limits and Common Mistakes

## Related Docs
```

Only use the headings the page actually needs. Stub docs should feel concise, not skeletal.

## Good and Bad Patterns

Bad:

> This module serializes state and orchestrates raster normalization.

Better:

> Use this page to prepare a soil burn severity raster for upload. It explains the raster styles WEPPcloud accepts and the validation issues that most often block an upload.

Bad:

> The run directory contains controller snapshots and multiple derived resources.

Better:

> WEPPcloud projects are file-based. This page shows where to find the main `.nodb`, terrain, landuse, soil, and WEPP output files inside a run directory.

## Review Checklist

Before publishing a stub doc, verify that:

- the first 100 words answer the main user question,
- the page stays focused on one narrow topic,
- each file path or artifact name is explicit and in monospace,
- optional or conditional files are labeled as such,
- the recommended path is clear when several options exist,
- the page does not drift into developer internals,
- related deeper docs are linked instead of copied into the stub.

## Usersum Publication Rules

When a stub doc should appear in usersum:

1. Keep the markdown in normal repo form with relative `.md` links.
2. Add the document to `wepppy/weppcloud/routes/usersum/docs_manifest.yaml`.
3. Add it to `wepppy/weppcloud/routes/usersum/nav_tree.yaml`.
4. Choose the lowest reasonable `min_role`. End-user stub docs should almost always be `user`.
5. Rebuild and validate the usersum index.

Relevant commands:

```bash
PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py validate --require-vendor-files
PYTHONPATH=/workdir/wepppy python3 tools/usersum_docs_tool.py build-index --write --require-vendor-files
wctl doc-lint --path wepppy/weppcloud/routes/usersum/weppcloud/enduser-stub-authoring-guide.md
```
