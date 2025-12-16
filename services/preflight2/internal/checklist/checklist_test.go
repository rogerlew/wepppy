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
