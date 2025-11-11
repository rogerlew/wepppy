package checklist

import (
	"log/slog"
	"os"
	"reflect"
	"strconv"
	"sync"
)

// Payload represents the structure delivered to WebSocket clients.
type Payload struct {
	Type         string          `json:"type"`
	Checklist    map[string]bool `json:"checklist"`
	LockStatuses map[string]bool `json:"lock_statuses"`
}

// Evaluate translates raw Redis hash data into the preflight checklist and lock statuses.
func Evaluate(prep map[string]string) (map[string]bool, map[string]bool) {
	debugDumpState("Evaluate", prep)

	check := map[string]bool{
		"sbs_map":         prep["attrs:has_sbs"] == "true",
		"channels":        hasKey(prep, "timestamps:build_channels"),
		"outlet":          false,
		"subcatchments":   false,
		"landuse":         false,
		"rangeland_cover": false,
		"soils":           false,
		"climate":         false,
		"rap_ts":          false,
		"rhem":            false,
		"wepp":            false,
		"omni_scenarios":  false,
		"observed":        false,
		"debris":          false,
		"watar":           false,
		"dss_export":      false,
	}

	buildChannels := prep["timestamps:build_channels"]
	outletTS := maxTimestamp(prep, "timestamps:set_outlet", "timestamps:find_outlet")
	check["outlet"] = safeGT(outletTS, buildChannels)
	check["subcatchments"] = safeGT(prep["timestamps:abstract_watershed"], buildChannels)
	check["landuse"] = safeGT(prep["timestamps:build_landuse"], prep["timestamps:abstract_watershed"])

	buildSoils := prep["timestamps:build_soils"]
	if safeGT(buildSoils, prep["timestamps:abstract_watershed"]) {
		afterLanduse := safeGT(buildSoils, prep["timestamps:build_landuse"])
		afterRangeland := safeGT(buildSoils, prep["timestamps:build_rangeland_cover"])
		check["soils"] = afterLanduse || afterRangeland
	}

	buildRangeland := prep["timestamps:build_rangeland_cover"]
	check["rangeland_cover"] = buildRangeland != ""

	check["climate"] = safeGT(prep["timestamps:build_climate"], prep["timestamps:abstract_watershed"])
	check["rap_ts"] = safeGT(prep["timestamps:build_rap_ts"], prep["timestamps:build_climate"])

	runWepp := firstTimestamp(prep, "timestamps:run_wepp_watershed", "timestamps:run_wepp")
	check["wepp"] = safeGT(runWepp, prep["timestamps:build_landuse"]) &&
		safeGT(runWepp, prep["timestamps:build_soils"]) &&
		safeGT(runWepp, prep["timestamps:build_climate"])

	check["observed"] = safeGT(prep["timestamps:run_observed"], prep["timestamps:build_landuse"]) &&
		safeGT(prep["timestamps:run_observed"], prep["timestamps:build_soils"]) &&
		safeGT(prep["timestamps:run_observed"], prep["timestamps:build_climate"]) &&
		safeGT(prep["timestamps:run_observed"], runWepp)

	check["debris"] = safeGT(prep["timestamps:run_debris"], prep["timestamps:build_landuse"]) &&
		safeGT(prep["timestamps:run_debris"], prep["timestamps:build_soils"]) &&
		safeGT(prep["timestamps:run_debris"], prep["timestamps:build_climate"]) &&
		safeGT(prep["timestamps:run_debris"], runWepp)

	check["watar"] = safeGT(prep["timestamps:run_watar"], prep["timestamps:build_landuse"]) &&
		safeGT(prep["timestamps:run_watar"], prep["timestamps:build_soils"]) &&
		safeGT(prep["timestamps:run_watar"], prep["timestamps:build_climate"]) &&
		safeGT(prep["timestamps:run_watar"], runWepp)

	check["omni_scenarios"] = safeGT(prep["timestamps:run_omni_scenarios"], runWepp)

	check["rhem"] = prep["timestamps:run_rhem"] != ""

	check["dss_export"] = safeGT(prep["timestamps:dss_export"], runWepp)

	locks := make(map[string]bool)
	for k, v := range prep {
		if len(k) > 7 && k[:7] == "locked:" {
			locks[k[7:]] = v == "true"
		}
	}

	debugDumpChecklist("Evaluate", check, locks)
	return check, locks
}

func hasKey(prep map[string]string, key string) bool {
	_, ok := prep[key]
	return ok
}

func safeGT(a, b string) bool {
	ai, aok := parseInt(a)
	bi, bok := parseInt(b)
	if !aok || !bok {
		return false
	}
	return ai > bi
}

func parseInt(raw string) (int64, bool) {
	if raw == "" {
		return 0, false
	}
	v, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return 0, false
	}
	return v, true
}

func firstTimestamp(prep map[string]string, keys ...string) string {
	for _, k := range keys {
		if v := prep[k]; v != "" {
			return v
		}
	}
	return ""
}

func maxTimestamp(prep map[string]string, keys ...string) string {
	var (
		maxVal int64
		found  bool
	)
	for _, k := range keys {
		if v, ok := parseInt(prep[k]); ok {
			if !found || v > maxVal {
				maxVal = v
				found = true
			}
		}
	}
	if !found {
		return ""
	}
	return strconv.FormatInt(maxVal, 10)
}

// Equal returns whether two payloads carry the same effective data.
func Equal(a, b Payload) bool {
	if a.Type != b.Type {
		return false
	}
	return reflect.DeepEqual(a.Checklist, b.Checklist) &&
		reflect.DeepEqual(a.LockStatuses, b.LockStatuses)
}

var (
	debugOnce sync.Once
	logger    *slog.Logger
)

func debugLogger() *slog.Logger {
	debugOnce.Do(func() {
		logger = slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
			Level: slog.LevelDebug,
		}))
	})
	return logger
}

func debugDumpState(label string, prep map[string]string) {
	debugLogger().Debug("checklist input", "label", label, "fields", prep)
}

func debugDumpChecklist(label string, checklist map[string]bool, locks map[string]bool) {
	debugLogger().Debug("checklist output", "label", label, "checklist", checklist, "locks", locks)
}
