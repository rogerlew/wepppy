"""Publish a complete verified matrix and four isolated project validations."""
import argparse
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import statistics

from tests.roads.extract_fixture import digest
from tests.roads.roads_analysis import SUITE, analyze, source_hashes
from tests.roads.roads_matrix import REFERENCE, site
from tests.roads.roads_project import DESIGNS


def number(value):
    return "—" if value is None else f"{value:.5g}"


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
                      *("| " + " | ".join(map(str, row)) + " |" for row in rows)]) + "\n"


def render(rows, projects, provenance):
    core = [r for r in rows if r["case"]["control"] == "core"]
    text = ["# Roads parameter validation — current results\n",
        "Site: **clogging-starch**. **516/516 profile cases completed**: 504 factorial combinations and 12 one-factor controls. "
        "All four textures—clay, loam, sand and silt—are included. Three full-upload additive checks and a separately qualified unrutted subset check completed; the full-upload unrutted control was rejected.\n",
        "## Scope and interpretation\n",
        "The common site climate contains 5,844 daily records, **2000–2015 (16 years)**; its legacy header advertises 100 years. "
        "The pinned `wepp_260409` hillslope executable matches the source project. "
        "Roads production builders and native PASS/WAT readers generated these results. "
        "This is a numerical and integration validation, not field calibration.\n",
        "Detachment is native full-profile detachment, averaged over all 16 years including zero-output days. "
        "For mixed profiles it includes road, fill, buffer and/or landuse OFEs; it is **not road-prism-only erosion**. "
        "Density divides by actual WAT full-profile area. Export is profile sediment leaving the slope, not watershed outlet yield. "
        "Different arrangements have different footprints, so their differences do not isolate routing alone.\n",
        "The seven arrangements are bare/rocked inslope direct (one OFE), bare/rocked road–buffer (two), "
        "rutted road–fill–buffer (three), and unrutted landuse–road–fill with/without downstream landuse (three/four). "
        "Each crosses three geometries, four soils, two surfaces and three traffic states.\n",
        "## Geometry and input assumptions\n",
        table(["Geometry", "Source segment", "Road length (m)", "Grade (%)"],
              [[g,v["segment_id"],number(v["segment_length_m"]),number(v["slope_pct_clamped"])] for g,v in site()["geometry"].items()]),
        "The shortest segment is about **8.6 mm**, a numerical/segmentation stress case. "
        "The lower median is only 2.62 m; these controls do not represent typical road lengths. "
        "Reference width is 4 m; requested rock fragments are 15%; fill/buffer/upstream landuse are each 30 m at 10%. "
        "Production mapping makes road rock content 65% for gravel or 95% for paved, fill 40%, and buffer/landuse 15%. "
        "The rock_0/rock_40 controls change fill and buffer/landuse rock content; road rock content stays fixed. "
        "These are experimental assumptions. Unrutted profiles use the production geometry transformation and bounds; "
        "slope-file lengths and widths are rounded to three decimals. WAT area is retained independently. "
        "Shared snow, ET and groundwater inputs come from the site; the legacy road plant names use the existing "
        "first-record ET coefficient fallback (0.95/0.8). These isolated profiles do not reproduce full-project strip allocation.\n",
        "## Four-texture comparison\n",
        "Roads texture keys clay/loam/sand/silt select legacy clay-loam/loam/sandy-loam/silt-loam templates. "
        "These matched rows hold median road geometry, gravel and low traffic fixed. "
        "Values are annual detachment, full-profile detachment density, deposition and sediment export.\n",
        table(["Texture", "Arrangement", "Area m²", "Detach kg/yr", "Detach kg/m²/yr", "Deposit kg/yr", "Export kg/yr"],
            [[r["case"]["texture"],r["case"]["arrangement"],*(number(r["summary"][k]) for k in
                ("modeled_area_m2","soil_loss_kg","soil_loss_density_kg_m2","sediment_deposition_kg","sediment_yield_kg"))]
             for r in core if r["case"]["geometry"] == "median" and r["case"]["surface"] == "gravel" and r["case"]["traffic"] == "low"]),
        "## Variability across the complete factorial matrix\n",
        "Each texture has 126 combinations. Ranges mix geometry, surface, traffic and arrangement; they are not uncertainty intervals.\n"]
    groups = []
    for texture in ("clay", "loam", "sand", "silt"):
        selected = [r["summary"]["soil_loss_density_kg_m2"] for r in core if r["case"]["texture"] == texture]
        groups.append([texture,len(selected),number(min(selected)),number(statistics.median(selected)),number(max(selected))])
    text += [table(["Texture", "Cases", "Min kg/m²/yr", "Median kg/m²/yr", "Max kg/m²/yr"],groups),
             "## Paired surface and traffic contrasts\n",
             "Within each pair all other factors remain fixed. Ratios are omitted when the denominator is zero; "
             "the suite does not impose a universal monotonic ranking.\n"]
    contrasts=[]
    for field, numerator, denominator in (("surface","paved","gravel"),("traffic","low","high"),("traffic","none","low")):
        lookup={tuple((k,v) for k,v in r["case"].items() if k != field):r for r in core if r["case"][field]==denominator}
        ratios=[]; zero=0; increases=0; count=0
        for r in core:
            if r["case"][field] != numerator: continue
            other=lookup[tuple((k,v) for k,v in r["case"].items() if k != field)]
            a,b=r["summary"]["soil_loss_density_kg_m2"],other["summary"]["soil_loss_density_kg_m2"]
            count+=1; increases+=a>b
            if b == 0: zero+=1
            else: ratios.append(a/b)
        contrasts.append([f"{numerator}/{denominator}", count, increases, zero,number(min(ratios) if ratios else None),number(statistics.median(ratios) if ratios else None),number(max(ratios) if ratios else None)])
    text += [table(["Detachment density ratio", "Pairs", "Numerator greater", "Zero denominator", "Min", "Median", "Max"],contrasts),
             "## One-factor sensitivity controls\n",
             "Reference: median geometry, rutted, loam, gravel, low traffic. Each control changes one requested input. "
             "The doubled grade requests 58.4865%; the production clamp emits 40%. Requested/effective geometry and clipping flags are retained.\n"]
    reference=next(r for r in rows if r["name"] == REFERENCE.name)
    selected=[reference]+[r for r in rows if r["case"]["control"] != "core"]
    text += [table(["Control", "Area m²", "Detach kg/yr", "Detach kg/m²/yr", "Runoff m³/yr", "Lateral m³/yr", "Baseflow m³/yr"],
        [[r["case"]["control"],*(number(r["summary"][k]) for k in ("modeled_area_m2","soil_loss_kg","soil_loss_density_kg_m2","runoff_volume_m3","subrunoff_volume_m3","baseflow_volume_m3"))] for r in selected]),
        "## Scientific assessment and exceptions\n", (SUITE / "analysis_context.md").read_text(),
        "## Separate full-project checks\n",
        "Fresh copies of the site were explicitly assigned each design and run through upload, preparation, "
        "execution and current-result publication. Unrutted requires explicit feature fill/buffer inputs: "
        "30 m at 10% each here. Daily area-weighted precipitation, lateral flow, percolation and ET components "
        "reconcile to persisted accounting WAT; runoff reconciles to canonical PASS volume. Current receipts and source/baseline hashes were checked. "
        "Site eligibility rules still skip segments; nonzero completed profiles and expected additive/replacement targets are required.\n",
        "**Full-upload unrutted rejection:** all 55 input features were retained. Two records failed the non-positive "
        "upstream-OFE guard at Topaz 271/272, and no current result receipt was published. "
        "The sampled downstream distance (188.45 m) exceeds the representative hillslope lengths (140.51/69.05 m); "
        "this is a limitation of the current profile representation, not proof that the physical road is impossible. "
        "The separate positive control excludes exactly source feature OSUNUM6 (54 of 55 inputs), whose identity is pinned. "
        "It proves feasible replacement integration, **not whole-site unrutted success or a like-for-like watershed design comparison**. "
        "Only one road replacement profile plus one remainder is exercised on one target hillslope; "
        "38 other crossing candidates are excluded by existing eligibility rules. Skipped manifest records in the table do not include those excluded candidates.\n",
        table(["Design", "Input features", "Prepared", "Completed profiles", "Skipped records", "Modeled area m²", "P mm/yr", "Runoff mm/yr", "Lateral mm/yr", "Baseflow mm/yr", "ET mm/yr"],
            [[p["design"] + (" (subset)" if p["selection"]["excluded"] else ""),p["selection"]["input_features"],p["prepared_features"],p["completed_profiles"],sum(p["skipped_reasons"].values()),number(p["reconciliation"]["modeled_area_m2"]),
              *(number(p["reconciliation"]["mean_annual_mm"][k]) for k in ("Precipitation","Runoff","Lateral Flow","Baseflow","ET"))] for p in projects]),
        "Baseline mean annual depths (same 16-year record): " + ", ".join(f"{k} {number(v)} mm" for k,v in projects[0]["reconciliation"]["baseline_mean_annual_mm"].items()) + ".\n",
        "## Reproducibility and limitations\n",
        "The suite discovered and repaired a no-traffic single-OFE management reference failure and a stray character "
        "in the paved sandy-loam rocked-ditch soil template. All plant definitions/references are now preserved. "
        "Fourteen previously working pilot PASS files were byte-identical after the management repair. "
        "Early clone attempts also exposed a stale-path logging side effect; final clones rebase paths before loading controllers. "
        "The original scientific outputs and saved state were unchanged.\n",
        f"Generated {provenance['generated_utc']}. Matrix definition: 516 unique cases; all complete calendars and finite required native metrics. "
        "Exact requested/emitted dimensions, source identities and generated input/output hashes are committed alongside the source report "
        "in `tests/roads/matrix_results_current.json` and `tests/roads/analysis_provenance_current.json`. "
        "Raw model artifacts remain in the retained validation roots. Repository freshness tests detect source/report drift. "
        "There is no claim of field accuracy, production deployment, or repair of existing project results.\n"]
    return "\n".join(text)


def publish(root, project_roots, negative_root):
    from wepppyo3 import wepp_interchange

    sources_before = source_hashes()
    rows=analyze(root)
    from tests.roads.roads_project import verify_negative, collect_evidence
    negative=verify_negative(Path("/wc1/runs/cl/clogging-starch"), negative_root)
    projects=[]
    for project_root in project_roots:
        p=json.loads((project_root / "validation.json").read_text())
        p = collect_evidence(Path("/wc1/runs/cl/clogging-starch"), project_root, p["design"])
        projects.append(p)
    if sorted(p["design"] for p in projects) != sorted(DESIGNS):
        raise ValueError("Require exactly four completed distinct full-project designs")
    native_root=Path(wepp_interchange.__file__).parent
    provenance=dict(generated_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=source_hashes(), negative_control=negative,
        execution_identity=json.loads((root / "execution-identity.json").read_text()), native_sha256={p.name:digest(p) for p in native_root.glob("*.so")},
        matrix_root=str(root), project_roots=list(map(str,project_roots)),
        case_artifacts=[{k:r[k] for k in ("name","input_sha256","output_sha256","template_sha256")} for r in rows])
    if not provenance["native_sha256"]:
        raise ValueError("Native extension identity missing")
    payload=dict(cases=[{k:r[k] for k in ("name","case","segment_run_id","requested","emitted","parity","ofe_order","clipping","effective_geometry","management_readback","summary")} for r in rows],
                 projects=[{k:v for k,v in p.items() if k not in ("prepared_inputs","receipt","params")} for p in projects])
    result_text = json.dumps(payload, indent=2, allow_nan=False) + "\n"
    provenance["results_sha256"] = hashlib.sha256(result_text.encode()).hexdigest()
    report_text = render(rows, projects, provenance)
    provenance["report_sha256"] = hashlib.sha256(report_text.encode()).hexdigest()
    provenance_text = json.dumps(provenance, indent=2, allow_nan=False) + "\n"
    if source_hashes() != sources_before:
        raise ValueError("Validation sources changed during publication")
    # Finish every scientific read and render before replacing current artifacts.
    artifacts = {"matrix_results_current.json":result_text, "analysis_results_current.md":report_text,
                 "analysis_provenance_current.json":provenance_text}
    for name, content in artifacts.items():
        (SUITE / (name + ".pending")).write_text(content)
    for name in artifacts:
        (SUITE / (name + ".pending")).replace(SUITE / name)



if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",type=Path)
    parser.add_argument("projects",type=Path,nargs=4)
    parser.add_argument("--unrutted-negative", type=Path, required=True)
    args=parser.parse_args()
    publish(args.root,args.projects,args.unrutted_negative)
