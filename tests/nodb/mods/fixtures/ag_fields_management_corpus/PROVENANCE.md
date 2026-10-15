# Management corpus fixtures

These are byte-for-byte snapshots of Forest's former local inputs
`tests/disturbed/disturbed_matrix0/runs/p1.man` and `p2.man`, captured on
2026-10-15. Each contains one OFE and a 100-year management sequence. The corpus
test combines them into a two-OFE management file and reparses the result.

Keep both files committed here. The test must not depend on ignored disturbed
matrix output or another test running first. Git attributes preserve original
bytes, including trailing spaces; these small text fixtures do not use LFS.

SHA-256:

- `p1.man`: `5ab3c1efd785288aacd5d8ef79730e4c8e4522b6902a1628c732a9e13ddcd066`
- `p2.man`: `43ae1f0df3df5d13fe6fe7892fc20792027820c45327ccf9c259d26445d4e0f6`
