"""Read paired existing outputs without mutating the project or interpreting lineage."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb


def fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.run / "wepp/output/interchange"
    sources = {name: root / f"H.{name}.parquet" for name in ("wat", "pass")}
    with duckdb.connect() as db:
        for name, path in sources.items():
            db.read_parquet(str(path)).create_view("w" if name == "wat" else "p")
        # Stable geometry and complete daily identities are checked before comparison.
        duplicates = {}
        for name, keys in (("w", "wepp_id,year,julian,ofe_id"),
                           ("p", "wepp_id,year,julian")):
            duplicates[name] = db.execute(
                f"SELECT count(*) FROM (SELECT {keys} FROM {name} GROUP BY ALL HAVING count(*)>1)"
            ).fetchone()[0]
        if any(duplicates.values()):
            raise ValueError(f"Duplicate daily identities: {duplicates}")
        invalid_geometry = db.execute("""
            SELECT count(*) FROM (
                SELECT wepp_id,ofe_id FROM w GROUP BY ALL
                HAVING count(DISTINCT Area) != 1 OR min(Area)<=0
                    OR bool_or(Area IS NULL OR NOT isfinite(Area)))
        """).fetchone()[0]
        if invalid_geometry:
            raise ValueError("Invalid or changing OFE geometry")
        db.execute("""CREATE TEMP VIEW comparison AS
            WITH a AS (
                SELECT wepp_id,sum(area) area FROM (
                    SELECT wepp_id,ofe_id,first(Area) area FROM w GROUP BY ALL)
                GROUP BY wepp_id),
            t AS (SELECT wepp_id,max(ofe_id) terminal FROM w GROUP BY wepp_id)
            SELECT w.wepp_id,w.year,w.julian,w.sim_day_index,
                   w.Q,w.QOFE,w.Area terminal_area,a.area hill_area,
                   p.event,p.runvol,p.runvol*1000/a.area pass_q,
                   w.latqcc*w.Area/1000 wat_lateral_volume,p.sbrunv
            FROM w JOIN t ON w.wepp_id=t.wepp_id AND w.ofe_id=t.terminal
            JOIN a ON w.wepp_id=a.wepp_id
            LEFT JOIN p ON w.wepp_id=p.wepp_id AND w.year=p.year AND w.julian=p.julian
            WHERE t.terminal>1
        """)

        def records(sql):
            result = db.execute(sql)
            names = [column[0] for column in result.description]
            return [dict(zip(names, row)) for row in result.fetchall()]

        receipt = {
            "sources": {name: fingerprint(path) for name, path in sources.items()},
            "duplicates": duplicates,
            "provenance_limit": "Configured binary name is not proof of the producer binary hash; no lineage inferred from Q/QOFE ratios.",
            "configured_binary": json.loads((args.run / "wepp.nodb").read_text())["py/state"].get("_wepp_bin"),
            "summary": records("""SELECT count(*) terminal_days,
                count(*) FILTER(WHERE event IS NULL) unmatched_pass_days,
                max(abs(Q-pass_q)) max_abs_q_difference_mm,
                avg(abs(Q-pass_q)) mean_abs_q_difference_mm,
                count(*) FILTER(WHERE Q>0 AND runvol=0) positive_wat_zero_pass_days
                FROM comparison""")[0],
            "by_event": records("""SELECT event,count(*) AS day_count,sum(Q) sum_terminal_q_mm,
                sum(pass_q) sum_pass_q_mm,max(abs(Q-pass_q)) max_abs_difference_mm
                FROM comparison GROUP BY event ORDER BY event"""),
            "largest_discrepancies": records("""SELECT * FROM comparison
                ORDER BY abs(Q-pass_q) DESC,wepp_id,year,julian LIMIT 12"""),
        }
    args.output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps(receipt["summary"], indent=2))


if __name__ == "__main__":
    main()
