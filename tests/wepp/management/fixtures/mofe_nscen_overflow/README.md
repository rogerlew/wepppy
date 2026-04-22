# MOFE `nscen` Overflow Fixtures

These fixtures are copied from production incident runs on `wepp1`.

Retrieved: `2026-04-22 14:26:38 PDT (-0700)`
Method: `scp` from `wepp1` host path `/geodata/wc1/runs/...`

## Source Runs

- `patrician-ambivalence`
  - `/geodata/wc1/runs/pa/patrician-ambivalence/wepp/runs/p386.man`
  - `/geodata/wc1/runs/pa/patrician-ambivalence/wepp/runs/p386.slp`
  - `/geodata/wc1/runs/pa/patrician-ambivalence/wepp/runs/p386.err`
- `congealed-inspector`
  - `/geodata/wc1/runs/co/congealed-inspector/wepp/runs/p1802.man`
  - `/geodata/wc1/runs/co/congealed-inspector/wepp/runs/p1802.slp`
  - `/geodata/wc1/runs/co/congealed-inspector/wepp/runs/p1802.err`

## Known Signature

- `nofe` in management section is 19.
- Serialized yearly scenario count (`nscen`) is inflated above 20.
- `.err` files contain WEPP hillslope failure:
  - `*** nmscen read as XX. Must be between 1 and 20 ***`
