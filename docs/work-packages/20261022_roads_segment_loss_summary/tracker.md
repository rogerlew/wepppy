# Roads segment summary tracker

Status: Active — implementation validated; consumer and broad gates underway.

- [x] Confirm target-first join reproduces duplicated results.
- [x] Record operator scope, compatibility plan and canonical contract/ADR.
- [x] Two independent contract approvals; standalone checkpoint `bac3042b1`.
- [x] Implement source-qualified aggregation; 76 focused tests pass.
- [x] Validate all UM1 rows, live Chromium/downloads, archive/restore and failure behavior.
- [ ] Complete focused/broad gates and independent final reviews; commit/close.

Starting WEPPpy: `61f17b0b7`. Native unchanged: `c941cb6`.
Unrelated UI/infrastructure/quality-report edits and native calendar/HBP edits
remain excluded. Closed Roads water-accounting package is immutable provenance.

Decision: each row represents its complete simulated source profile; unsupported
prism/buffer attribution is NULL. The canonical contract and ADR-0103 govern.
