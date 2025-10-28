---
name: doc-janitor
description: Nightly documentation hygiene maintenance flow (pilot)
schedule: "0 9 * * *"  # 09:00 UTC placeholder — adjust during rollout
agent_profile: code_supervisor
script: ../scripts/doc_janitor.sh
enabled: false
---

# Doc Janitor Flow Prompt (Placeholder)

This flow currently runs the `doc_janitor.sh` script, which emits a dry-run checklist.  
Real automation will overwrite this body with a templated prompt once the pilot is approved.
