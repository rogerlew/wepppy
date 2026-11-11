package streamauth

import (
	"encoding/base64"
	"encoding/json"
	"strings"
	"testing"
)

func TestRedactionAndCompatibility(t *testing.T) {
	for _, s := range []string{
		"Working in /wc1/runs/example/input.sol",
		`POLARIS job options: {"token":"fixture-sensitive"}`,
		"Ron.set_option -> fixture-sensitive",
		"Ron.set_option ->\nfixture-sensitive",
		"POLARIS job options:\nfixture-sensitive",
		"rq:job EXCEPTION ValueError: fixture-sensitive",
		`rq:job EXCEPTION_JSON {"message":"fixture-sensitive","stacktrace":"fixture-sensitive","scheme":"wepp","field_id":1}`,
		"Authorization: Bearer fixture-sensitive",
	} {
		out := SanitizeStatus(s)
		if strings.Contains(out, "fixture-sensitive") || strings.Contains(out, "/wc1/") {
			t.Fatal("redaction failed")
		}
	}
	for _, s := range []string{"Building soils: 50%", "rq:job TRIGGER wepp WEPP_RUN_TASK_COMPLETED", "rq:job COMPLETE run_sync_rq(example, cfg)"} {
		if SanitizeStatus(s) != s {
			t.Fatal("control compatibility failed")
		}
	}
}

func TestStructuredDiagnosticsAndException(t *testing.T) {
	fields := map[string]any{"schema_version": 1, "operation_id": strings.Repeat("a", 32), "root_job_id": "root", "producer_job_id": "producer", "method": "fill", "elevation_unit": "m", "maximum_raise": 2.5, "maximum_cut": 0, "summary": "Raised in /wc1/private/file"}
	raw, _ := json.Marshal(fields)
	prefix := "rq:producer TRIGGER channel CONDITIONING_DIAGNOSTICS "
	out := SanitizeStatus(prefix + "DIAGNOSTICS_V1:" + base64.RawURLEncoding.EncodeToString(raw))
	encoded := strings.Fields(strings.TrimPrefix(out, prefix+"DIAGNOSTICS_V1:"))[0]
	decoded, err := base64.RawURLEncoding.DecodeString(encoded)
	if err != nil {
		t.Fatal("invalid encoded diagnostics")
	}
	var got map[string]any
	if json.Unmarshal(decoded, &got) != nil || len(got) != 9 || got["root_job_id"] != "root" || got["producer_job_id"] != "producer" || got["maximum_raise"] != 2.5 {
		t.Fatal("diagnostics consumer schema lost")
	}
	if strings.Contains(string(decoded), "/wc1/") {
		t.Fatal("diagnostics path leaked")
	}
	fields["schema_version"] = 2
	raw, _ = json.Marshal(fields)
	if strings.Contains(SanitizeStatus("DIAGNOSTICS_V1:"+base64.RawURLEncoding.EncodeToString(raw)), "DIAGNOSTICS_V1:") {
		t.Fatal("invalid schema accepted")
	}
	out = SanitizeStatus(`rq:job EXCEPTION_JSON {"scheme":"wepp","field_id":1,"filename":"/wc1/private/input.sol","message":"private detail"}`)
	var exception map[string]any
	json.Unmarshal([]byte(strings.SplitN(out, "EXCEPTION_JSON ", 2)[1]), &exception)
	if exception["filename"] != "input.sol" || exception["field_id"] != float64(1) || strings.Contains(out, "private") {
		t.Fatal("exception consumer schema or redaction failed")
	}
}
