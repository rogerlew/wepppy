# Read-only reader correction scientific review

Disposition: accepted for rereading the twelve already executed cases; no native rerun is authorized or needed by this correction.

The original reader incorrectly assumed the last emitted boundary equaled native depth and grouped all SCON events before all hourly initialization events. My execution prereview missed these assumptions. Retain the original reader, declaration and failed validations.

Pinned INPUT adds 200 mm to the final boundary at line 572, caps boundaries at 1800 mm at line 591, and resamples on a 200 mm grid beginning at line 698. The v2 formula min(emitted+200,1800) is appropriate for the declared grid-aligned cases, not a general replacement for native horizon interpretation. The first completed trace confirms 400 mm emitted support becomes 600 mm computational support. Observed initialization order is per OFE: SCON layers followed by hourly initialization layers.

The versioned reader preserves emitted and computational depths, checks actual layer identities/depths, and otherwise retains the reviewed native arithmetic. The rereader checks paired computational support, original inputs and output identity controls, and verifies campaign inventory unchanged. The v4 synthetic controls retain eleven rejection cases. This is a correction to observation interpretation, not retention behavior.

Profile stocks must use observed computational thickness. Extra native support is common to both lanes and cannot be described as a candidate retention effect. Neither emitted nor realized controlled support reconstructs a source field profile. Actual result acceptance remains pending completed reread receipts.

## Bindings

- `docs/work-packages/20261101_retention_volume_prototype/artifacts/read_native_v2.py`: `230ec8c5223a49f127059ffa6092671efe217dda012e7e7b7cbaa319b3911525`
- `docs/work-packages/20261101_retention_volume_prototype/artifacts/read_campaign_v2.py`: `ab8bf3d87f327f9346a33e726b527c5d7d313520856fa090ef6d9cdac8af7381`
- `out/retention-volume-prototype-20261101/reader-controls-v4/receipt.json`: `31dffb6ad095da191dc8d4327739c706cc7b7bfae200bc7f0058ae4dd1de6880`
- `out/roads-parameterization-program-20261031/buffer-storage-ownership-r4/native-probe/build/src/input.for`: `362a328510298eb86f682b248256ae43c8b36ca15b6cf2d6dd1887999ae275df`
