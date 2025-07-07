#!/usr/bin/env python3
import sys
import re
import json
import pandas as pd

def build_popup_html(row):
    """
    Build an HTML <h4> + <ul>…</ul> string from a pandas Series (row).
    Excludes 'lat' and 'lon'. Extracts 'sitenum' from 'site_name' and appends
    a URL at the end.
    """
    # 1. Station name
    site_name = row.get("site_name", "")
    html_parts = [f"<h4>{site_name}</h4>"]
    html_parts.append('<ul class="textattributes">')

    # 2. For each column except 'lat','lon','site_name','Unnamed:…', emit a <li>
    for col, val in row.items():
        if col in ("lat", "lon", "site_name"):
            continue
        # Skip empty/NaN or placeholder columns (like 'Unnamed: 10')
        if pd.isna(val) or col.startswith("Unnamed"):
            continue

        # Convert to string and escape basic HTML characters
        val_str = str(val)
        # (If you need stronger escaping, import html and do html.escape(val_str))
        col_name = col.upper()
        html_parts.append(
            f'  <li><strong><span class="atr-name">{col_name}</span>:</strong> '
            f'<span class="atr-value">{val_str}</span></li>'
        )

    # 3. Extract sitenum from site_name, e.g. "Anchor River Divide (1062)"
    sitenum_match = re.search(r"\((\d+)\)", site_name)
    sitenum = sitenum_match.group(1) if sitenum_match else ""
    if sitenum:
        url = f"https://wcc.sc.egov.usda.gov/nwcc/site?sitenum={sitenum}"
        html_parts.append(
            '  <li><strong><span class="atr-name">SITENUM</span>:</strong> '
            f'<span class="atr-value">{sitenum}</span></li>'
        )
        html_parts.append(
            '  <li><strong><span class="atr-name">URL</span>:</strong> '
            f'<span class="atr-value"><a href="{url}" target="_blank">{url}</a></span></li>'
        )

    html_parts.append("</ul>")
    return "\n".join(html_parts)


def csv_to_geojson(input_csv_path, output_geojson_path):
    # 1. Load CSV into pandas
    df = pd.read_csv(input_csv_path)

    # 2. Make sure 'lat' and 'lon' exist
    if "lat" not in df.columns or "lon" not in df.columns:
        raise KeyError("CSV must contain 'lat' and 'lon' columns.")

    features = []
    for _, row in df.iterrows():
        lat = row["lat"]
        lon = row["lon"]
        try:
            lat = float(lat)
            lon = float(lon)
        except ValueError:
            # skip rows with invalid coords
            continue

        # Build the HTML for the popup
        popup_html = build_popup_html(row)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "Description": popup_html,
                "Name": row.get("site_name", "")
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    # 3. Write to file
    with open(output_geojson_path, "w", encoding="utf-8") as fout:
        json.dump(geojson, fout, ensure_ascii=False, indent=2)

    print(f"→ Wrote {len(features)} features to {output_geojson_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python csv_to_geojson.py <input.csv> <output.geojson>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_geojson = sys.argv[2]
    csv_to_geojson(input_csv, output_geojson)