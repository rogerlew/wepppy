"""Certify two observed REAL arithmetic residuals without changing the frozen audit.

All error comparisons use exact rational values of the recovered binary32 inputs.
The certificate applies only to the retained cases and source/trace/output hashes.
"""
import argparse
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import struct

U = Q(1, 2**24)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def real(value):
    return struct.unpack("f", struct.pack("f", float(value)))[0]


def gamma(n):
    return n * U / (1 - n * U)


def half_ulp(value):
    value = real(abs(value))
    bits = struct.unpack("I", struct.pack("f", value))[0]
    up = struct.unpack("f", struct.pack("I", bits + 1))[0]
    down = struct.unpack("f", struct.pack("I", bits - 1))[0]
    return max(Q(up) - Q(value), Q(value) - Q(down)) / 2


def observed(root, label, record):
    folder = root / "runs" / label
    receipt_path = folder / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    assert receipt["exact_output_parity"] and receipt["returncode"] == 0
    assert receipt["source_record_sha256"] == sha(record)
    assert receipt["binary_sha256"] == sha(root / "wepp")
    assert receipt["trace_sha256"] == sha(folder / "trace.txt")
    assert receipt["outputs"] == json.loads(record.read_text())["outputs"]
    for name, digest in receipt["outputs"].items():
        assert sha(folder / "output" / name) == digest
    return [line.split() for line in (folder / "trace.txt").read_text().splitlines()], receipt


def grid_certificate(lines):
    result = []
    for ofe in ("2", "3"):
        rows = [line for line in lines if line[0] == "PM_GRID" and line[3] == ofe]
        if not rows:
            continue
        theta, initial, final = real(rows[0][8]), real(rows[0][6]), real(rows[-1][7])
        width = sum(Q(real(line[5])) for line in rows)
        assert width == 1 and len(rows) == 101
        details = []
        previous = initial
        for line in rows:
            x, dx, old, new, th, eata = map(real, line[4:10])
            assert eata == 0 and th == theta and old == previous
            assert min(dx, old, new, th) >= 2**-126
            product = real(dx * th)
            increment = real(real(real(real(product + real(2 * product)) + real(2 * product)) + product) / 6)
            replay = max(real(old + increment), real(old + product))
            assert replay == new
            # Product, three positive additions, division; factors of two are exact.
            # The Euler lower bound has a smaller error bound than this RK4 branch.
            error = Q(new) - Q(old) - Q(th) * Q(dx)
            bound = half_ulp(new) + gamma(5) * abs(Q(th) * Q(dx))
            assert abs(error) <= bound
            details.append(dict(x=x, dx=dx, old=old, new=new, error=float(error),
                                absolute_error_bound=float(bound), exact_native_replay=True))
            previous = new
        total_bound = sum(half_ulp(row["new"]) + gamma(5) * Q(theta) * Q(row["dx"]) for row in details)
        deficit = Q(initial) + Q(theta) * width - Q(final)
        assert abs(deficit) <= total_bound
        result.append(dict(ofe=int(ofe), steps=len(rows), total_width=float(width), theta=theta,
                           initial=initial, final=final, constant_source_deficit=float(deficit),
                           derived_absolute_error_bound=float(total_bound), steps_detail=details))
    return result


def mix_certificate(lines):
    tagged = {}
    for tag in ("PM_SOURCE", "PM_MIX", "PM_MIX_OUT"):
        tagged[tag] = {tuple(line[1:6]): list(map(real, line[6:]))
                       for line in lines if line[0] == tag}
    result = []
    for key, values in tagged["PM_SOURCE"].items():
        if key not in tagged["PM_MIX"]:
            continue
        fractions, soil, interrill = values[:5], values[5:10], values[10:15]
        load, incoming, source, raw_rill = tagged["PM_MIX"][key]
        rill = max(0, raw_rill)
        assert min(values) >= 0 and min(load, incoming, source, rill) >= 0 and load > 0
        target = tagged["PM_MIX_OUT"][key][1:]
        replay = [real(real(real(real(a * incoming) + real(b * rill)) + real(c * source)) / load)
                  for a, b, c in zip(fractions, soil, interrill)]
        assert replay == target
        ideal = (sum(map(Q, fractions)) * Q(incoming) + sum(map(Q, soil)) * Q(rill)
                 + sum(map(Q, interrill)) * Q(source)) / Q(load)
        native = sum(map(Q, target))
        bound = gamma(6) * abs(ideal)
        assert abs(native - ideal) <= bound
        result.append(dict(key=key, incoming_fractions=fractions, soil_fractions=soil,
                           interrill_fractions=interrill, load=load, upstream_load=incoming,
                           interrill=source, raw_rill=raw_rill, native_fractions=target,
                           native_fraction_sum=float(native), exact_weighted_fraction_sum=float(ideal),
                           mix_rounding_error=float(native - ideal), mix_rounding_bound=float(bound),
                           matched_native_fractions=True))
    return result


def class_certificate(lines, final_fractions):
    rows = [line for line in lines if line[0] == "PM_CLASS"]
    assert len(rows) == 1
    line = rows[0]
    total, *values = map(real, line[5:11])
    sequential = 0.0
    for value in values:
        assert value >= 2**-126
        sequential = real(sequential + value)
    assert sequential == total
    replay = [real(value / total) for value in values]
    assert replay == final_fractions
    excess = sum(map(Q, replay)) - 1
    bound = (gamma(4) + U) / (1 - gamma(4))
    assert abs(excess) <= bound
    return dict(key=line[1:5], class_loads=values, native_sequential_sum=total,
                exact_class_sum=float(sum(map(Q, values))), native_fractions=replay,
                normalization_error=float(excess), derived_normalization_bound=float(bound),
                exact_native_replay=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Retained observation bundle")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = json.loads((root / "retention-manifest.json").read_text())
    for name, digest in manifest["files"].items():
        assert sha(root / name) == digest, name
    result = dict(root=str(root), script_sha256=sha(Path(__file__)),
                  retention_manifest_sha256=sha(root / "retention-manifest.json"),
                  unit_roundoff=float(U), exact_rational_error_checks=True,
                  strict_audit_unchanged=True, cases={})
    for label, event in (("denver_fraction", ["8", "228"]), ("site_fraction", ["2003", "29"])):
        record_path = root / "source-records" / label / "record.json"
        record = json.loads(record_path.read_text())
        lines, receipt = observed(root / "arithmetic", label, record_path)
        rows = [line for line in lines if line[0] == "PM_SLOSS" and line[1:3] == event]
        assert len(rows) == 1
        row = rows[0]
        avsole = real(row[4])
        fractions = list(map(real, row[-5:]))
        excess = sum(map(Q, fractions)) - 1
        width = record["width_m"]
        case = dict(source_record_sha256=sha(record_path), original_source=receipt["source"],
                    trace_sha256=receipt["trace_sha256"], output_hashes=receipt["outputs"],
                    exact_output_parity=True, width_m_from_original_record=width,
                    grid=grid_certificate(lines), mix=mix_certificate(lines),
                    native_fractions=fractions, native_fraction_sum=float(excess + 1),
                    native_fraction_excess=float(excess), bulk_avsole_kg_m=avsole,
                    implied_excess_mass_kg=float(Q(avsole) * Q(width) * excess))
        if label == "site_fraction":
            class_lines, class_receipt = observed(root / "class_normalization", label, record_path)
            case["class_trace_sha256"] = class_receipt["trace_sha256"]
            case["class_normalization"] = class_certificate(class_lines, fractions)
        result["cases"][label] = case
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Both retained residuals replay exactly and satisfy source-derived arithmetic bounds.")


if __name__ == "__main__":
    main()
