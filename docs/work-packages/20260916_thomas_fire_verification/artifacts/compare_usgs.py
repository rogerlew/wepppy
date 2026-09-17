"""Compare public USGS basin polygons and M1 predictors without run writes."""
import json
import math
from pathlib import Path
import fiona
import numpy as np
import rasterio
from rasterio.features import shapes, rasterize
from pyproj import Transformer
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent
RUN = Path("/wc1/runs/ne/nervous-mesquite")


def main():
    saved = json.loads((ROOT / "saved_run_audit.json").read_text())
    with rasterio.open(RUN / "postfire_debris_flow/attempts" / saved["attempt"] / "predictors/prepared/mask.tif") as raster:
        a = raster.read(1, masked=True).filled(0) > 0
        basin = unary_union([shape(g) for g,v in shapes(a.astype("uint8"), mask=a, transform=raster.transform) if v == 1])
        crs = raster.crs
        grid_transform = raster.transform
        grid_shape = raster.shape
    with fiona.open(ROOT / "thm2017_Basin_DFPredictions_15min_24mmh.shp") as ref:
        project = Transformer.from_crs(crs, ref.crs, always_xy=True)
        basin = transform(project.transform, basin)
        outlet = transform(project.transform, Point(259038.91793810797,3815153.6325536324))
        matches = []
        for f in ref:
            geometry = shape(f["geometry"])
            if not geometry.intersects(basin):
                continue
            overlap = geometry.intersection(basin).area
            matches.append((overlap, geometry, dict(f["properties"])))
        matches.sort(key=lambda v: v[0], reverse=True)
        overlap, geometry, fields = matches[0]
        best = fields["BASIN_ID"]
        reference_crs = str(ref.crs)
    with fiona.open(ROOT / "thm2017_basinpt_feat.shp") as points:
        near = sorted([(shape(f["geometry"]).distance(outlet), dict(f["properties"]), mapping(shape(f["geometry"]))) for f in points], key=lambda v:v[0])[:3]
    ours = saved["raster"]["independent_predictors"]
    theirs = dict(zip(("T","F","S"), (fields["L_X1"],fields["L_X2"],fields["L_X3"])))

    def prob(p, rainfall=6, duration=15):
        b,ct,cf,cs = {15:(-3.63,.41,.67,.70),30:(-3.61,.26,.39,.50),60:(-3.21,.17,.20,.22)}[duration]
        return 1/(1+math.exp(-(b+rainfall*(ct*p["T"]+cf*p["F"]+cs*p["S"]))))

    logit_parts = {k:6*c*(ours[k]-theirs[k]) for k,c in zip(("T","F","S"),(.41,.67,.70))}
    alternative = dict(ours, S=theirs["S"])
    grid_geometry = transform(Transformer.from_crs(reference_crs, crs, always_xy=True).transform, geometry)
    reference_cells = rasterize([(mapping(grid_geometry),1)], out_shape=grid_shape, transform=grid_transform).astype(bool)
    pred = RUN / "postfire_debris_flow/attempts" / saved["attempt"] / "predictors"
    with rasterio.open(pred / "valid_mask.tif") as raster:
        common = raster.read(1, masked=True).filled(0) > 0
    overlap_predictors = {}
    for key, path in [("T",pred/"wbt/intersection.tif"),("F",pred/"prepared/dnbr.tif"),
                      ("S",RUN/"rusle/k_polaris_nomograph.tif")]:
        with rasterio.open(path) as raster:
            values = raster.read(1,masked=True).astype("float64")
            overlap_predictors[key] = float(values[common & reference_cells].mean())
    rounded_error = abs(prob(theirs)-fields["P"])
    # USGS DBF predictors are rounded to six decimals. Sigmoid derivative <= 1/4.
    rounded_bound = 6 * (.41+.67+.70) * .5e-6 / 4 + 1e-11
    evidence = dict(reference_crs=reference_crs, run_crs=str(crs),
                    datum_transform=project.description, best_match_basin=best,
                    geometry=dict(run_area_km2=basin.area/1e6, usgs_area_km2=geometry.area/1e6,
                                  intersection_km2=overlap/1e6, intersection_over_union=overlap/basin.union(geometry).area,
                                  fraction_run_inside_usgs=overlap/basin.area,
                                  fraction_usgs_inside_run=overlap/geometry.area,
                                  run_outlet_distance_to_usgs_polygon_m=outlet.distance(geometry)),
                    top_overlap_basins=[dict(basin_id=p["BASIN_ID"],overlap_km2=a/1e6) for a,g,p in matches[:5]],
                    nearest_usgs_pourpoints=near, usgs_fields=fields,
                    run_predictors=ours, usgs_predictors=theirs,
                    run_predictors_on_shared_spatial_support=overlap_predictors,
                    usgs_rounded_predictor_probability_error=rounded_error,
                    usgs_rounding_error_bound=rounded_bound,
                    I15_24=dict(run_probability=prob(ours),usgs_probability=fields["P"],
                               independently_recomputed_usgs_probability=prob(theirs),
                               probability_difference_points=100*(prob(ours)-fields["P"]),
                               run_with_only_usgs_soil=prob(alternative),
                               logit_difference_contributions=logit_parts,
                               soil_share_of_net_logit_difference=logit_parts["S"]/sum(logit_parts.values())),
                    usgs_P50_intensity_mm_h=3.63/(.41*theirs["T"]+.67*theirs["F"]+.70*theirs["S"])*4,
                    run_P50_intensity_mm_h=saved["inverse"][0]["intensity_mm_per_hour"])
    (ROOT / "usgs_comparison.json").write_text(json.dumps(evidence, indent=2)+"\n")
    # Retain just the matched public feature as a convenient portable reference.
    (ROOT / "usgs_basin_19384.geojson").write_text(json.dumps(dict(type="Feature", properties=fields,
        geometry=mapping(transform(Transformer.from_crs(reference_crs,4326,always_xy=True).transform,geometry))),indent=2)+"\n")
    print(json.dumps(evidence,indent=2))
    assert best == 19384 and rounded_error <= rounded_bound


if __name__ == "__main__":
    main()
