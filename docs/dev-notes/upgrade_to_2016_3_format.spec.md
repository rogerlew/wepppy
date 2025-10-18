# upgrade_to_2016_3_format specification

This document outlines the expectations for a utility that upgrades an existing
WEPP `98.4` management file to the `2016.3`/`2017.1` layout while preserving the
behavior of the original scenario. The goal is to normalize legacy entries so
that they can coexist with newer management libraries and participate in
composite rotations without hand editing.

## High-level goals

1. Accept a parsed `Management` instance representing a 98.4 file and return a
   new 2016.3-compatible `Management` (or write one to disk).
2. Keep agronomic behavior unchanged—new parameters introduced in 2016.3 should
   be populated with neutral defaults (generally `0.0` or `0`).
3. Produce text output that the existing parser, configured for `datver`
   `2016.3`/`2017.1`, will accept without additional intervention.

## Required steps

1. **Version metadata**
   - Set `datver` to `"2016.3"` (or `"2017.1"` if we prefer the latest tag).
   - Update any cached numeric version (`datver_value`) to `2016.3` so helper
     logic recognizes the upgraded file as “new-format”.

2. **Plant section (cropland loops)**
   - Ensure every cropland plant loop exposes an `rcc` attribute.
   - When the legacy file lacks the value, insert `0.0` and include it when the
     plant section is rendered.

3. **Operation section (cropland loops)**
   - Append residue resurfacing fractions to the seven-value operation data line
     (positions 8.8 and 8.9 in the manual).
     - Use `0.0 0.0` for `resurf1`/`resurnf1` in the upgrade path.
   - Accounts for operation codes that require additional lines in 2016.3 (10,
     11, 12, 13, 14, 15, 18, 19). For 98.4 sources we only expect codes
     1–4 and 10–13, but the upgrade should still emit the placeholder extra line
     if the code appears. Fill the new fields (e.g. residue removal/shredding
     fractions) with `0.0` or leverage existing 98.4 data when available.

4. **Initial condition section (cropland loops)**
   - Extend the final line to include the understory cover entries (`usinrco`,
     `usrilco`) and set both to `0.0`.

5. **Contour section**
   - Append the `contours_perm` flag and default it to `0` (temporary) when the
     source file lacks the value.

6. **Preservation of remaining content**
   - Leave surface effects, drainage, yearly scenarios, and management loop data
     untouched beyond updating `datver`. These sections did not gain new fields
     in 2016.3, and any scenario references should remain valid.

7. **Validation**
   - After transforming the in-memory object, optionally re-parse the generated
     text with `Management.load` to verify it is accepted as a 2016.3 file.
   - Consider returning the new object and/or providing a helper that writes out
     the upgraded text file.

## Implementation notes

- Work on a deep copy of the input `Management` to avoid mutating shared state
  when multiple callers reuse the same base management.
- Helper functions that serialize loops already honor optional fields when the
  attribute is present. Ensure the upgrade step sets the new attributes so the
  string formatter writes them automatically.
- For traceability, the writer may insert a commented header explaining that the
  file was upgraded automatically, though the utility should also support a pure
  object-returning mode for programmatic use.

