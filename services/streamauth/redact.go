package streamauth

import (
	"encoding/base64"
	"encoding/json"
	"math"
	"path/filepath"
	"regexp"
	"strings"
)

var absolutePath = regexp.MustCompile(`(?i)(?:[a-z]:[\\/]|\\\\|/)[^\s"'<>\]\[{},;()]+`)
var bearer = regexp.MustCompile(`(?i)bearer[. ]+[A-Za-z0-9_.~+/-]+`)
var jwtText = regexp.MustCompile(`[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}`)
var secretAssignment = regexp.MustCompile(`(?i)(password|secret|token|api[_-]?key|authorization)["']?\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;}]+)`)
var setter = regexp.MustCompile(`(?s)([A-Za-z0-9_]+\.[A-Za-z0-9_]+) ->\s*.*`)
var optionsMap = regexp.MustCompile(`(?is)(job options:).*`)
var safeIdentifier = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,128}$`)

func cleanText(s string) string {
	s = bearer.ReplaceAllString(s, "[credential]")
	s = jwtText.ReplaceAllString(s, "[credential]")
	s = secretAssignment.ReplaceAllString(s, "$1=[redacted]")
	s = absolutePath.ReplaceAllString(s, "[path]")
	s = setter.ReplaceAllString(s, "$1 -> [redacted]")
	return optionsMap.ReplaceAllString(s, "$1 [redacted]")
}

// SanitizeStatus preserves parser control tokens while removing confirmed disclosure classes.
func SanitizeStatus(data string) string {
	if at := strings.Index(data, "EXCEPTION_JSON"); at >= 0 {
		var raw map[string]any
		safe := map[string]any{"message": "Operation failed. Inspect the authorized job report for details."}
		if json.Unmarshal([]byte(strings.TrimSpace(data[at+len("EXCEPTION_JSON"):])), &raw) == nil {
			for _, key := range []string{"scheme", "field_id", "sub_field_id"} {
				switch value := raw[key].(type) {
				case string:
					if safeIdentifier.MatchString(value) {
						safe[key] = value
					}
				case float64:
					if !math.IsNaN(value) && !math.IsInf(value, 0) {
						safe[key] = value
					}
				}
			}
			if filename, ok := raw["filename"].(string); ok {
				safe["filename"] = cleanText(filepath.Base(strings.ReplaceAll(filename, `\`, "/")))
			}
		}
		encoded, _ := json.Marshal(safe)
		return cleanText(data[:at]) + "EXCEPTION_JSON " + string(encoded)
	}
	if at := strings.Index(data, "EXCEPTION"); at >= 0 {
		return cleanText(data[:at]) + "EXCEPTION Operation failed. Inspect the authorized job report for details."
	}
	if strings.Contains(data, "Traceback (most recent call last)") || strings.Contains(data, "File \"") {
		return "Operation failed. Inspect the authorized job report for details."
	}
	if at := strings.Index(data, "DIAGNOSTICS_V1:"); at >= 0 {
		prefix, rest := data[:at], data[at+len("DIAGNOSTICS_V1:"):]
		encoded, tail, _ := strings.Cut(rest, " ")
		raw, err := base64.RawURLEncoding.DecodeString(encoded)
		var fields map[string]any
		if err != nil || len(raw) > 4096 || json.Unmarshal(raw, &fields) != nil {
			return cleanText(prefix + tail)
		}
		safe := map[string]any{"schema_version": 1}
		valid := fields["schema_version"] == float64(1) && fields["elevation_unit"] == "m"
		method, _ := fields["method"].(string)
		valid = valid && (method == "fill" || method == "breach" || method == "breach_least_cost" || method == "topaz")
		operation, _ := fields["operation_id"].(string)
		valid = valid && regexp.MustCompile(`^[0-9a-f]{32}$`).MatchString(operation)
		for _, key := range []string{"operation_id", "root_job_id", "producer_job_id", "method", "elevation_unit", "summary"} {
			value, ok := fields[key].(string)
			valid = valid && ok && len(value) > 0 && len(value) <= 1000
			if key != "summary" {
				valid = valid && safeIdentifier.MatchString(value)
			}
			safe[key] = cleanText(value)
		}
		for _, key := range []string{"maximum_raise", "maximum_cut"} {
			n, ok := fields[key].(float64)
			valid = valid && ok && n >= 0 && !math.IsNaN(n) && !math.IsInf(n, 0)
			safe[key] = n
		}
		if !valid {
			return cleanText(prefix + tail)
		}
		raw, _ = json.Marshal(safe)
		return cleanText(prefix) + "DIAGNOSTICS_V1:" + base64.RawURLEncoding.EncodeToString(raw) + " " + cleanText(tail)
	}
	// Arbitrary summary objects can contain paths/options under unrecognized keys.
	trimmed := strings.TrimSpace(data)
	if strings.HasPrefix(trimmed, "{") || strings.HasPrefix(trimmed, "[") {
		return "Operation summary available in the project report."
	}
	return cleanText(data)
}
