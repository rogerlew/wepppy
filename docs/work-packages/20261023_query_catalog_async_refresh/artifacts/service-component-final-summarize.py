"""Summarize only sanitized retained final-sample profiling evidence."""
import collections
import json
import math
import statistics
from pathlib import Path

base = Path(__file__).parent
raw = json.loads((base / "service-component-final.json").read_text())
rows = raw["reused"] + raw["results"]
selected = {digest for group in raw["manifest"]["sample_digests"].values() for digest in group}
assert len({row["digest"] for row in rows}) == len(rows)
assert all(row["digest"] in selected for row in rows)
source_hashes = {json.dumps(event["source_sha256"], sort_keys=True)
                 for row in rows for event in row["events"] if event["event"] == "start"}
summary = {"selected": len(selected), "measured": len(rows),
           "unattempted": len(selected) - len(rows), "source_hash_sets": len(source_hashes),
           "blocked_mutations": [], "paired_entry_differences": [], "namespaces": {}}
for row in rows:
    for event in row["events"]:
        summary["blocked_mutations"].extend(event.get("blocked_mutations", []))
    passes = [event for event in row["events"] if event["event"] == "pass"]
    if row["exit_code"] == 0:
        assert [event["attempt"] for event in passes] == [1, 2]
        assert row["events"][-1]["status"] == "passed"
    for event in passes:
        for key in ("collect_seconds", "verify_seconds", "component_seconds"):
            assert math.isfinite(event[key]) and event[key] >= 0
    if len(passes) == 2 and passes[0]["entries_sha256"] != passes[1]["entries_sha256"]:
        summary["paired_entry_differences"].append(row["digest"])
for namespace in raw["manifest"]["sample_digests"]:
    group = [row for row in rows if row["namespace"] == namespace]
    good = [row for row in group if row["exit_code"] == 0]
    stat = {"attempted": len(group), "completed": len(good),
            "timeouts": sum(row["execution_status"] == "timeout" for row in group),
            "errors": sum(row["exit_code"] not in (0, None) for row in group)}
    for attempt in (1, 2):
        events = [event for row in group for event in row["events"]
                  if event["event"] == "pass" and event["attempt"] == attempt]
        collections_done = [event for row in group for event in row["events"]
                            if event["event"] == "phase" and event.get("phase") == "verify"
                            and event["attempt"] == attempt]
        stat["pass" + str(attempt)] = {"completed_passes": len(events),
                                     "completed_collections": len(collections_done)}
        for key in ("collect_seconds", "verify_seconds", "component_seconds", "entry_count"):
            selected_events = collections_done if key in ("collect_seconds", "entry_count") else events
            values = [event[key] for event in selected_events]
            stat["pass" + str(attempt)][key] = {
                "min": min(values), "mean": statistics.mean(values), "max": max(values)} if values else None
    summary["namespaces"][namespace] = stat
(base / "service-component-final-summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
