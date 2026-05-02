# Ablation Templates (Local)

This directory provides the local template files required by `tools/ablation_protocol.py`:

- `TEMPLATE_incident.md`
- `TEMPLATE_notes.md`
- `TEMPLATE_matrix.csv`
- `TEMPLATE_artifacts.md`

Use:

```bash
python tools/ablation_protocol.py init --incident-id <YYYYMMDD_runid_scope_signature>
python tools/ablation_protocol.py finalize --incident-id <YYYYMMDD_runid_scope_signature>
```

Notes:
- These templates are aligned with the current `wepp-forest` ablation workflow contract.
- Some template guidance references additional cross-repo artifacts (for example watchlists or policy docs) that may live in `wepp-forest`.
