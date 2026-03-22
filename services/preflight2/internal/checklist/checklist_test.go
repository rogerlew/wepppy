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
