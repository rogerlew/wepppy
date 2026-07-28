# SHR-04A Base and Macro Field Matrix

| Producer family | Material contract | Final evidence |
| --- | --- | --- |
| `base_pure.htm` | metadata, body state, blocks, script order | `test_base_pure_renders_document_metadata_blocks_and_assets` |
| Shells/panels | form identity, input-before-panel order, status, summary, stacktrace, hints | `test_pure_control_shell_renders_form_and_lifecycle_contract` plus DOM consumers |
| Text/select/numeric/file | id/name/value/state/help/error/attrs | `test_pure_field_macros_preserve_identity_values_state_and_aria` |
| Radio/checkbox/textarea | tokens, selected/checked/disabled state | producer tests plus completed DOM consumers |
| Tabs/tables/slots/scales | identities, ARIA, empty/hidden state | `test_pure_choice_and_structural_macros_preserve_state_and_targets` |
| Cards/fieldsets/display/empty table | structure, attributes, actions, empty state | `test_pure_card_and_empty_state_macros_render_structure` |

Transport, JavaScript lifecycle, modal/theme behavior, and unit-conversion
semantics remain with SHR-02, SHR-03A, SHR-04B, and SHR-05 respectively.

All 105 tests in `test_pure_controls_render.py` pass. No producer mismatch was
found and no production template changed.
