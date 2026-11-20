# Historical vendor source checkpoint

The first real rebuild found five previously served WEPP Forest files absent
from the active ref. The upstream archive commit
`2f65506d239b449bbb73c6820ff9cb949fa55158` contains them. Four published mirrors
match those committed blobs and one differs. The operator requested removing
stale copies and keeping one authoritative copy. Preserve existing public
URLs by declaring the upstream archive ref and the five historical seeds.
The active commit wins path collisions. Rebuilds still prune files outside
the graph and replace stale bytes. Keep the existing manifest and generated
index identity for the historical brief.

The implementation reviews confirmed the previous release-note 404 and flagged
the risk of removing the registered brief. Both reviewers recommended committed
historical sources. They also identified role checks on canonical and alias
routes, temporary snapshot visibility, and unvalidated Git tree names.
The durable specification records the corresponding obligations. Acceptance
includes the existing historical page route, archive precedence, copied byte
readback, and unchanged role behavior across serving entry points.
