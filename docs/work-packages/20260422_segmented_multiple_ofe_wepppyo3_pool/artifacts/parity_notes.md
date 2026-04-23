# MOFE Segmentation Parity Notes

- Source run: `/wc1/runs/po/pointy-toed-fluff`
- Source slope files checked: `3345`
- Comparison: wepppyo3 production path (`segmented_multiple_ofe`) vs deprecated Python legacy path (`segmented_multiple_ofe_legacy`).
- Parameters:
  - `target_length=60.0`
  - `buffer_length=30.0`
  - `max_ofes=19`

- Mismatches: `0`
- Result: all checked `.mofe.slp` outputs and segment counts matched exactly.

Raw machine-readable data: `artifacts/parity_raw.json`
