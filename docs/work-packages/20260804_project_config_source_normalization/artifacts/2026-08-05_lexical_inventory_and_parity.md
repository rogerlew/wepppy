# WP00B Lexical Inventory and Semantic Parity

## Corpus Boundary

The source corpus at starting revision `2c3816bd49` contains `_defaults.toml`
and 128 top-level `.cfg` named presets: 129 files and 3,341 assignments. The
139 `legacy/*.toml` snapshots and one `batch/*.cfg` file are excluded because
they are compatibility or batch inputs rather than future resolver sources.

## Pre-Normalization Inventory

| Lexical form | Count |
| --- | ---: |
| integer | 858 |
| double-quoted string | 738 |
| `None` | 625 |
| lowercase boolean | 438 |
| finite float | 293 |
| plain list | 291 |
| bare string | 49 |
| trailing-comma list | 31 |
| capitalized boolean | 14 |
| legacy tuple list | 2 |
| inline numeric comment | 1 |
| single-quoted string | 1 |

## Post-Normalization Inventory

| Canonical type | Count |
| --- | ---: |
| integer | 859 |
| string | 788 |
| null | 625 |
| boolean | 452 |
| list | 324 |
| finite float | 293 |

The inline comment is now a standalone comment immediately before its integer
assignment. No comment content was lost. Every assignment uses exactly one
ratified encoding, and a second normalizer run reports zero drift.

## Semantic-Parity Method

For each source, the starting bytes are read from Git at `2c3816bd49` and the
working bytes are decoded into section/option maps using the accepted legacy
lexical rules. Inline comments are removed only at the same scalar boundary
used by current integer/float accessors. The resulting typed maps are compared
for exact equality.

    semantic parity passed: 129 active/default sources
    project-config sources validated: 129 file(s); changed=0

This proves source values are unchanged. It intentionally does not claim raw
byte equality, because standardizing bytes is the purpose of WP00B.

The first broad test run caught the two tuple lists after they were incorrectly
quoted as strings. WP00B then added an explicit legacy tuple decoder, converted
both to canonical lists, reran typed parity, and passed the affected rq-engine
catalog route plus the complete repository suite.

## Compatibility Notes

Canonical source lists remain Python-literal compatible because the current
reader uses `ast.literal_eval`. Strings are double-quoted; the current string
accessor removes those delimiters. Booleans remain compatible with the
case-insensitive boolean accessor. Null remains `None`, the deployed reader's
existing sentinel.
