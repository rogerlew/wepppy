"""Read-only GDAL discovery/digest costs on actual NFS input sets, no native work."""
import hashlib
import json
from pathlib import Path
from statistics import mean
from time import sleep
from unittest.mock import patch

from osgeo import gdal
from wepppy.all_your_base import file_digest
from raster_recursive_correctness_probe import graph


def main():
    gdal.UseExceptions()
    groups = {
        "sbs_original": [Path("/wc1/runs/th/thespian-cleanness/disturbed/GrizzlyCreek_SBS_final.tif")],
        "sbs_cropped": [Path("/wc1/runs/th/thespian-cleanness/disturbed/baer.cropped.tif")],
        "dem": [Path("/wc1/runs/th/thespian-cleanness/dem/dem.tif")],
        "rap_39_years_cropped": sorted(Path("/wc1/runs/ol/old-fluorosis/rap").glob("_rap_v3_*.tif")),
    }
    assert len(groups["rap_39_years_cropped"]) == 39
    result = {"scope": "read-only named NFS paths; no models/locks/controller writes; OS cache not dropped",
              "gdal_version": gdal.VersionInfo(), "groups": {}}
    for name, paths in groups.items():
        before = [graph(path) for path in paths]
        original = {member: file_digest.sha256_file(member, use_cache=False)
                    for observation in before for member in observation["digests"]}
        file_digest._observed_at.cache_clear()
        file_digest._digest.cache_clear()
        real_factory = file_digest.hashlib.sha256
        measurements = []
        for index in range(12):
            if index == 1:
                sleep(1.05)  # Immutable sources: isolate normal one-second admission.
            computations = []
            def count(*args, **kwargs):
                computations.append(1)
                return real_factory(*args, **kwargs)
            with patch.object(file_digest.hashlib, "sha256", side_effect=count):
                observed = [graph(path) for path in paths]
            assert {member: digest for item in observed for member, digest in item["digests"].items()} == original
            measurements.append({"phase": "cold" if index == 0 else "admit" if index == 1 else "settled",
                "seconds": sum(item["seconds"] for item in observed),
                "discovery_seconds": sum(item["discovery_seconds"] for item in observed),
                "digest_computations": len(computations)})
        after = {member: file_digest.sha256_file(member, use_cache=False) for member in original}
        assert original == after
        settled = measurements[2:]
        result["groups"][name] = {"selected_paths": list(map(str, paths)), "member_count": len(original),
            "bytes": sum(Path(member).stat().st_size for member in original),
            "named_bytes_unchanged": original == after, "measurements": measurements,
            "settled_mean_seconds": mean(item["seconds"] for item in settled),
            "settled_discovery_mean_seconds": mean(item["discovery_seconds"] for item in settled),
            "settled_digest_computations": sum(item["digest_computations"] for item in settled)}
    result["probe_sha256"] = hashlib.sha256(Path(__file__).with_name("raster_recursive_correctness_probe.py").read_bytes()).hexdigest()
    output = json.dumps(result, indent=2)
    print(output)
    Path(__file__).with_suffix(".json").write_text(output + "\n")


if __name__ == "__main__":
    main()
