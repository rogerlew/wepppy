"""Build privacy-safe charts and CSV tables for the WEPPcloud usage report."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"
TABLES = ROOT / "tables"


def load(name: str) -> dict:
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def save_chart(name: str) -> None:
    CHARTS.mkdir(exist_ok=True)
    plt.tight_layout()
    plt.savefig(CHARTS / f"{name}.svg", bbox_inches="tight")
    plt.savefig(CHARTS / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close()


def write_csv(name: str, header: list[str], rows: list[list[object]]) -> None:
    TABLES.mkdir(exist_ok=True)
    with (TABLES / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    database = load("database_summary.json")
    access = load("access_summary.json")
    landing = load("landing_map_summary.json")
    project_quality = load("project_creation_quality_summary.json")
    landuse = load("landuse_proxy_summary.json")

    years = sorted(project_quality["by_year"])
    raw_project_counts = [
        project_quality["by_year"][year]["raw_database_records"] for year in years
    ]
    human_project_counts = [
        project_quality["by_year"][year]["human_evidenced_projects"]
        for year in years
    ]
    government_project_counts = [
        project_quality["email_domain_sector_by_year"][year]["government"]
        for year in years
    ]
    education_project_counts = [
        project_quality["email_domain_sector_by_year"][year]["education"]
        for year in years
    ]
    other_project_counts = [
        project_quality["email_domain_sector_by_year"][year]["other"]
        for year in years
    ]
    write_csv(
        "projects_created_by_year.csv",
        [
            "year",
            "raw_database_records",
            "human_evidenced_projects",
            "government_domain_projects",
            "education_domain_projects",
            "other_domain_projects",
        ],
        [
            [year, raw_count, human_count, government, education, other]
            for year, raw_count, human_count, government, education, other in zip(
                years,
                raw_project_counts,
                human_project_counts,
                government_project_counts,
                education_project_counts,
                other_project_counts,
                strict=True,
            )
        ],
    )
    plt.figure(figsize=(9, 4.8))
    x = list(range(len(years)))
    width = 0.38
    plt.bar(
        [value - width / 2 for value in x],
        raw_project_counts,
        width,
        color="#94a3b8",
        label="Raw database records",
    )
    plt.bar(
        [value + width / 2 for value in x],
        human_project_counts,
        width,
        color="#2563eb",
        label="Human-evidenced projects",
    )
    plt.xticks(x, years)
    plt.title("Raw project records versus human-evidenced projects")
    plt.ylabel("Project records")
    plt.xlabel("Year (2026 through September 28)")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    save_chart("projects_created_by_year")

    plt.figure(figsize=(9, 4.8))
    x = list(range(len(years)))
    plt.bar(x, government_project_counts, color="#1d4ed8", label="Government domains")
    plt.bar(
        x,
        education_project_counts,
        bottom=government_project_counts,
        color="#7c3aed",
        label="Education domains",
    )
    government_and_education = [
        government + education
        for government, education in zip(
            government_project_counts, education_project_counts, strict=True
        )
    ]
    plt.bar(
        x,
        other_project_counts,
        bottom=government_and_education,
        color="#94a3b8",
        label="Other domains",
    )
    for x_value, count in zip(x, human_project_counts, strict=True):
        plt.annotate(
            f"{count:,}",
            (x_value, count),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )
    plt.xticks(x, years)
    plt.title("Human-evidenced WEPPcloud projects created by year and domain sector")
    plt.ylabel("Human-evidenced projects created")
    plt.xlabel("Year (2020 begins in August; 2026 through September 28)")
    plt.ylim(0, max(human_project_counts) * 1.15)
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    save_chart("human_evidenced_projects_by_year")

    landuse_labels = {
        "natural_seminatural_dominant": "Natural / semi-natural dominant",
        "agriculture_dominant": "Agriculture dominant",
        "developed_dominant": "Developed dominant",
        "water_snow_barren_dominant": "Water / snow / barren dominant",
        "mixed_agriculture_natural": "Mixed agriculture / natural",
        "mixed_or_other": "Mixed / other / indeterminate",
    }
    landuse_colors = {
        "natural_seminatural_dominant": "#15803d",
        "agriculture_dominant": "#ca8a04",
        "developed_dominant": "#dc2626",
        "water_snow_barren_dominant": "#0284c7",
        "mixed_agriculture_natural": "#84cc16",
        "mixed_or_other": "#94a3b8",
    }
    landuse_rows = []
    for year, human_count in zip(years, human_project_counts, strict=True):
        values = landuse["by_year"].get(year, {})
        classified = values.get("classified_projects", 0)
        landuse_rows.append(
            [
                year,
                human_count,
                classified,
                100 * classified / human_count if human_count else 0,
                *[values.get(key, 0) for key in landuse_labels],
                values.get("missing_landuse_parquet", 0),
                values.get("unsupported_locale_or_source", 0),
                values.get("unclassified_parquet", 0),
            ]
        )
    write_csv(
        "landuse_proxy_by_year.csv",
        [
            "year",
            "human_evidenced_projects",
            "projects_with_classified_landuse_parquet",
            "classified_coverage_pct",
            *landuse_labels,
            "missing_landuse_parquet",
            "unsupported_locale_or_source",
            "unclassified_parquet",
        ],
        landuse_rows,
    )
    fig, left = plt.subplots(figsize=(10, 5.2))
    x = list(range(len(years)))
    bottom = [0] * len(years)
    for offset, (key, label) in enumerate(landuse_labels.items(), start=4):
        values = [row[offset] for row in landuse_rows]
        left.bar(x, values, bottom=bottom, color=landuse_colors[key], label=label)
        bottom = [old + value for old, value in zip(bottom, values, strict=True)]
    right = left.twinx()
    coverage = [row[3] for row in landuse_rows]
    right.plot(
        x,
        coverage,
        marker="o",
        linewidth=2.2,
        color="#111827",
        label="Classified coverage",
    )
    left.set_xticks(x, years)
    left.set_title("Human-evidenced projects with retained land-use classifications")
    left.set_xlabel("Creation year (2026 through September 28)")
    left.set_ylabel("Projects with classified land-use Parquet")
    right.set_ylabel("Share of human-evidenced projects classified (%)")
    right.set_ylim(0, 100)
    left.grid(axis="y", alpha=0.25)
    handles_left, labels_left = left.get_legend_handles_labels()
    handles_right, labels_right = right.get_legend_handles_labels()
    left.legend(handles_left + handles_right, labels_left + labels_right, loc="upper left")
    save_chart("landuse_proxy_by_year")

    access_years = sorted(access["by_year"])
    access_rows = [
        [
            year,
            access["by_year"][year]["access_events"],
            access["by_year"][year]["distinct_projects_accessed"],
            access["by_year"][year]["distinct_authenticated_users"],
            access["by_year"][year]["projects_first_seen_in_retained_logs"],
        ]
        for year in access_years
    ]
    write_csv(
        "retained_access_by_year.csv",
        [
            "year",
            "access_events",
            "distinct_projects_accessed",
            "distinct_authenticated_users",
            "projects_first_seen_in_retained_logs",
        ],
        access_rows,
    )
    fig, left = plt.subplots(figsize=(9, 4.8))
    right = left.twinx()
    left.plot(
        access_years,
        [row[1] for row in access_rows],
        marker="o",
        linewidth=2.5,
        color="#0f766e",
        label="Access events",
    )
    right.plot(
        access_years,
        [row[3] for row in access_rows],
        marker="s",
        linewidth=2.5,
        color="#c2410c",
        label="Distinct authenticated users",
    )
    left.set_title("Retained project access and authenticated users")
    left.set_xlabel("Year (2019 and 2026 are partial)")
    left.set_ylabel("Project access events", color="#0f766e")
    right.set_ylabel("Distinct authenticated users", color="#c2410c")
    left.grid(axis="y", alpha=0.25)
    lines = left.lines + right.lines
    left.legend(lines, [line.get_label() for line in lines], loc="upper left")
    save_chart("retained_access_and_users_by_year")

    sectors = access["authenticated_user_sector_by_domain"]
    sector_labels = {
        "government": "Government",
        "university_or_education": "University / education",
        "personal_email_provider": "Personal email",
        "commercial_or_other": "Commercial / other",
        "nonprofit_or_organization": "Nonprofit / organization",
    }
    ordered_sectors = sorted(sectors, key=sectors.get, reverse=True)
    write_csv(
        "authenticated_users_by_sector.csv",
        ["sector", "distinct_authenticated_users"],
        [[sector_labels[key], sectors[key]] for key in ordered_sectors],
    )
    plt.figure(figsize=(9, 4.8))
    plt.barh(
        [sector_labels[key] for key in reversed(ordered_sectors)],
        [sectors[key] for key in reversed(ordered_sectors)],
        color="#7c3aed",
    )
    plt.title("Authenticated users in retained project logs, by email-domain sector")
    plt.xlabel("Distinct users (571 total)")
    plt.grid(axis="x", alpha=0.25)
    save_chart("authenticated_users_by_sector")

    all_states = sorted(
        landing["us_state_counts"].items(), key=lambda item: item[1], reverse=True
    )
    states = all_states[:15]
    write_csv(
        "landing_map_points_by_state.csv",
        ["state", "active_georeferenced_projects"],
        [[state, count] for state, count in all_states],
    )
    plt.figure(figsize=(9, 6))
    plt.barh(
        [state for state, _ in reversed(states)],
        [count for _, count in reversed(states)],
        color="#15803d",
    )
    plt.title("Landing-map projects: top 15 matched U.S. states")
    plt.xlabel("Active georeferenced projects")
    plt.grid(axis="x", alpha=0.25)
    save_chart("landing_map_top_states")

    registration_years = [
        year for year in sorted(database["users"]["registration_year"]) if year != "unknown"
    ]
    registration_counts = [
        database["users"]["registration_year"][year] for year in registration_years
    ]
    write_csv(
        "known_confirmations_by_year.csv",
        ["year", "accounts_with_confirmed_at"],
        [
            [year, count]
            for year, count in zip(registration_years, registration_counts, strict=True)
        ],
    )
    plt.figure(figsize=(9, 4.8))
    plt.bar(registration_years, registration_counts, color="#9333ea")
    plt.title("Accounts with a known confirmation timestamp")
    plt.ylabel("Accounts")
    plt.xlabel("Year (4,447 accounts lack a confirmation timestamp)")
    plt.grid(axis="y", alpha=0.25)
    save_chart("known_confirmations_by_year")


if __name__ == "__main__":
    main()
