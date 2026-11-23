# Comrak Markdown migration

Replace cmarkgfm across WEPPpy with Comrak and provide Python extension
options and structured links. Keep existing Usersum permalinks, README
editing workflows and Browse rendering. The user authorized the replacement
and Python extension scaffold on 2026-11-20 UTC.

Use the [Markdown rendering contract](../../schemas/markdown-rendering-contract.md).
The complexity budget is one pinned Python wheel and one shared adapter.
The preceding Usersum vendor graph branch is the base so vendor traversal
and Docs Quality migrate with runtime rendering. Security impact is high
because project authors can submit README Markdown. Verify actual
rendered responses, authorization, raw HTML, unsafe URLs and the image
dependency. No deployment is included.

See the [tracker](tracker.md) and [execution plan](prompts/active/implementation_execplan.md).

Local implementation and validation are complete. The scoped Docker test
image and recorded wheel provenance are the validation baseline.
