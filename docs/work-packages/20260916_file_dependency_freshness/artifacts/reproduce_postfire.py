"""Baseline probe: real WEPP hard-link preparation, no named project writes."""
import json
import os
import tempfile
from pathlib import Path
from wepppy.nodb.mods.postfire_debris_flow import production as p
from wepppy.runtime_paths.wepp_inputs import copy_input_file

with tempfile.TemporaryDirectory(prefix='freshness-baseline-') as tmp:
    root = Path(tmp)
    source = root / 'climate' / 'wepp.cli'
    source.parent.mkdir()
    source.write_bytes(b'unchanged climate input\n')
    before = p.signature(root, source, strong=True)
    copy_input_file(str(root), 'climate/wepp.cli', root / 'wepp/runs/pw0.cli')
    linked = p.signature(root, source, strong=True)
    linked_current = p.artifacts_current(root, {"artifacts": {"climate/wepp.cli": before}}, strong=False)
    old_stat = source.stat()
    source.write_bytes(b'CHANGED!! climate input\n')
    os.utime(source, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    rewritten = p.signature(root, source, strong=True)
    result = {'before': before, 'linked': linked, 'rewritten_restored_mtime': rewritten,
              'hardlink_same_content': before[-1] == linked[-1],
              'hardlink_snapshot_equal': before[:4] == linked[:4],
              'hardlink_artifacts_current': linked_current,
              'rewrite_same_size_mtime': linked[1:3] == rewritten[1:3],
              'rewrite_changed_digest': linked[-1] != rewritten[-1],
              'uid': os.getuid(), 'gid': os.getgid()}
    print(json.dumps(result, indent=2))
