# Comrak Markdown migration tracker

## Progress

- [x] Inventory cmarkgfm call sites and compare available bindings.
- [ ] Review and commit the contract checkpoint.
- [ ] Implement the shared adapter and migrate production and build consumers.
- [ ] Validate rendered output, native dependency, and rollout readiness.

## Decisions

The feature branch is `task/comrak-markdown-migration`. It starts at the
Usersum vendor graph implementation `547ada295`. Select `comrak-ext`
because its published wheel exposes the syntax tree and embeds Comrak 0.59.0.
See the [contract decision](artifacts/20261120_contract_decision.md).
