# SHR-05 Unitizer Contract Matrix

| Boundary | Risk-bearing contract | Final evidence |
| --- | --- | --- |
| Global radios | `unit_main_selector`, values `0`/`1`, persisted aggregate state | direct render + client, verified |
| Category radios | exact category names, generated tokens, checked preference | direct render + map parity, verified |
| Modal | stable id, dialog label, dismiss targets | direct render, verified |
| Client | map load, global/category sync, labels, numeric canonical values | Node/Jest, verified |
| Project bridge | delegated changes, complete JSON payload, lifecycle events | 31 Project Jest, verified |
| Route | current-run context, JSON/form parsing, compatible filtering | route pytest, verified |
| Persistence/reload | lock/dump accepted preferences and re-render checked state | NoDb + render pytest, verified |
| Generated map | category/unit/token/conversion parity | builder pytest, verified |

No RQ or worker boundary exists for preference mutation.
