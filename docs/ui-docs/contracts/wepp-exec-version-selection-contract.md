# WEPP Exec version selection

This contract applies to **WEPP Advanced Options > WEPP Exec** on the run page.

- Offer the explicit versions allowed for the project. Exclude the deprecated
  `latest` alias from the choices a user can pick.
- If the saved version is `latest`, display it as the current value and keep
  the saved setting until the user picks an explicit version. Show the
  deprecation hint only while `latest` is selected.
- Preserve [executable capability and validation rules](../../schemas/wepp-executable-selection-contract.md#run-page-deprecation-of-latest-2026-11-20)
  and the existing pin to `wepp_dcc52a6`.

This retains compatibility for saved projects while making the executable
version explicit for future selections. Changing what an alias means would
make reruns harder to reproduce and trace.
