package checklist

import "testing"

func TestExtractLastModifiedPrefersExplicitField(t *testing.T) {
	ts := ExtractLastModified(map[string]string{
		"last_modified":       "1700000000",
		"timestamps:run_wepp": "1600000000",
	})

	if ts == nil {
		t.Fatalf("expected last_modified pointer, got nil")
	}
	if *ts != 1700000000 {
		t.Fatalf("unexpected value %d", *ts)
	}
}

func TestExtractLastModifiedFallsBackToTimestamps(t *testing.T) {
	ts := ExtractLastModified(map[string]string{
		"timestamps:run_wepp":           "1600000000",
		"timestamps:build_landuse":      "1500000000",
		"timestamps:run_wepp_watershed": "1650000000",
	})

	if ts == nil {
		t.Fatalf("expected derived last_modified, got nil")
	}
	if *ts != 1650000000 {
		t.Fatalf("unexpected value %d", *ts)
	}
}

func TestEvaluateRusleRequiresClimateAndWeppFreshness(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:build_climate":       "100",
		"timestamps:run_wepp_watershed":  "200",
		"timestamps:build_rusle":         "250",
		"timestamps:build_landuse":       "90",
		"timestamps:build_soils":         "95",
		"timestamps:abstract_watershed":  "80",
		"timestamps:build_channels":      "70",
		"timestamps:set_outlet":          "75",
		"timestamps:build_subcatchments": "85",
	})

	if !check["rusle"] {
		t.Fatalf("expected rusle checklist entry to be true when newer than climate + wepp")
	}
}

func TestEvaluateRusleBecomesStaleWhenClimateIsNewer(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:build_climate":      "300",
		"timestamps:run_wepp_watershed": "200",
		"timestamps:build_rusle":        "250",
	})

	if check["rusle"] {
		t.Fatalf("expected rusle checklist entry to be false when climate is newer")
	}
}

func TestEvaluateWeppSatisfiedByRusleForGriddedRuns(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "110",
		"timestamps:build_climate": "120",
		"timestamps:build_rusle":   "130",
	})

	if !check["rusle"] {
		t.Fatalf("expected rusle checklist entry to be true for fresh gridded RUSLE output")
	}
	if !check["wepp"] {
		t.Fatalf("expected wepp checklist entry to be true when gridded RUSLE is fresher than prerequisites")
	}
}

func TestEvaluateWeppNotSatisfiedByStaleRusleForGriddedRuns(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "110",
		"timestamps:build_climate": "140",
		"timestamps:build_rusle":   "130",
	})

	if check["wepp"] {
		t.Fatalf("expected wepp checklist entry to remain false when gridded RUSLE is stale")
	}
}

func TestEvaluateRoadsRequiresWeppFreshness(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:run_wepp_watershed": "200",
		"timestamps:run_roads":          "210",
	})

	if !check["roads"] {
		t.Fatalf("expected roads checklist entry to be true when run_roads is newer than WEPP")
	}
}

func TestEvaluateRoadsStaysFalseWithoutRunWepp(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:run_roads": "210",
	})

	if check["roads"] {
		t.Fatalf("expected roads checklist entry to be false when WEPP timestamp is missing")
	}
}

func TestEvaluateGenevaRequiresFreshCoreDependencies(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:run_geneva":    "400",
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "200",
		"timestamps:build_climate": "300",
	})

	if !check["geneva"] {
		t.Fatalf("expected geneva checklist entry to be true when run_geneva is fresher than prerequisites")
	}
}

func TestEvaluateGenevaStaleWhenClimateIsNewer(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"timestamps:run_geneva":    "250",
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "200",
		"timestamps:build_climate": "300",
	})

	if check["geneva"] {
		t.Fatalf("expected geneva checklist entry to be false when climate timestamp is newer")
	}
}

func TestEvaluateGenevaRequiresInitSbsMapWhenSbsEnabled(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"attrs:has_sbs":            "true",
		"timestamps:run_geneva":    "350",
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "200",
		"timestamps:build_climate": "300",
		"timestamps:init_sbs_map":  "360",
	})

	if check["geneva"] {
		t.Fatalf("expected geneva checklist entry to be false when SBS map is newer than run_geneva")
	}
}

func TestEvaluateGenevaIgnoresInitSbsMapWhenSbsDisabled(t *testing.T) {
	check, _ := Evaluate(map[string]string{
		"attrs:has_sbs":            "false",
		"timestamps:run_geneva":    "350",
		"timestamps:build_landuse": "100",
		"timestamps:build_soils":   "200",
		"timestamps:build_climate": "300",
		"timestamps:init_sbs_map":  "360",
	})

	if !check["geneva"] {
		t.Fatalf("expected geneva checklist entry to stay true when SBS dependency is inactive")
	}
}
