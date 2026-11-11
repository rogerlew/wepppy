package streamauth

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	miniredis "github.com/alicebob/miniredis/v2"
	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"
)

func claimsFor(service string) jwt.MapClaims {
	now := time.Now().Unix()
	return jwt.MapClaims{"iss": "weppcloud-stream", "aud": "wepp-" + service, "token_class": "session",
		"stream": service, "scope": service + ":read", "runid": "example", "config": "cfg", "sub": "sid",
		"session_id": "sid", "jti": "jti", "iat": now, "nbf": now, "exp": now + 300}
}
func signed(t *testing.T, c jwt.MapClaims) string {
	t.Helper()
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, c).SignedString([]byte("fixture-key"))
	if err != nil {
		t.Fatal("signing failed")
	}
	return token
}
func TestAuthorizationMatrix(t *testing.T) {
	for _, service := range []string{"status", "preflight"} {
		t.Run(service, func(t *testing.T) {
			cases := []struct {
				name   string
				mutate func(jwt.MapClaims)
				fence  string
				status int
			}{
				{"valid", func(c jwt.MapClaims) {}, "", 0},
				{"wrong issuer", func(c jwt.MapClaims) { c["iss"] = "other" }, "", 401},
				{"wrong audience", func(c jwt.MapClaims) { c["aud"] = "rq-engine" }, "", 401},
				{"array audience", func(c jwt.MapClaims) { c["aud"] = []string{"wepp-" + service} }, "", 401},
				{"wrong scope", func(c jwt.MapClaims) { c["scope"] = "rq:status" }, "", 401},
				{"wrong class", func(c jwt.MapClaims) { c["token_class"] = "user" }, "", 401},
				{"wrong stream", func(c jwt.MapClaims) { c["stream"] = "other" }, "", 401},
				{"cross run", func(c jwt.MapClaims) { c["runid"] = "other" }, "", 401},
				{"wrong config", func(c jwt.MapClaims) { c["config"] = "other" }, "", 401},
				{"expired", func(c jwt.MapClaims) { c["exp"] = time.Now().Unix() - 1 }, "", 401},
				{"future", func(c jwt.MapClaims) { c["iat"] = time.Now().Unix() + 30; c["nbf"] = c["iat"] }, "", 401},
				{"missing exp", func(c jwt.MapClaims) { delete(c, "exp") }, "", 401},
				{"missing nbf", func(c jwt.MapClaims) { delete(c, "nbf") }, "", 401},
				{"fractional iat", func(c jwt.MapClaims) { c["iat"] = float64(time.Now().Unix()) + .5 }, "", 401},
				{"excess lifetime", func(c jwt.MapClaims) { c["exp"] = time.Now().Unix() + 600 }, "", 401},
				{"subject mismatch", func(c jwt.MapClaims) { c["sub"] = "other" }, "", 401},
				{"missing marker", func(c jwt.MapClaims) {}, "marker", 401},
				{"revoked SID", func(c jwt.MapClaims) {}, "sid", 401},
				{"revoked JTI", func(c jwt.MapClaims) {}, "jti", 401},
				{"partial operation", func(c jwt.MapClaims) { c["operation"] = "run-sync" }, "", 403},
			}
			for _, tc := range cases {
				t.Run(tc.name, func(t *testing.T) {
					m := miniredis.RunT(t)
					key := filepath.Join(t.TempDir(), "key")
					if err := os.WriteFile(key, []byte("fixture-key"), 0600); err != nil {
						t.Fatal(err)
					}
					v, err := New(key, &redis.Options{Addr: m.Addr(), DB: 2}, []string{"https://example.test"})
					if err != nil {
						t.Fatal(err)
					}
					defer v.Close()
					ctx := context.Background()
					if tc.fence != "marker" {
						v.sessions.Set(ctx, "auth:session:run:example:sid", "1", time.Hour)
					}
					if tc.fence == "sid" {
						v.sessions.Set(ctx, "auth:session:revoked:sid", "1", time.Hour)
					}
					if tc.fence == "jti" {
						v.revoked.Set(ctx, "auth:jwt:revoked:jti", "1", time.Hour)
					}
					c := claimsFor(service)
					tc.mutate(c)
					r := httptest.NewRequest("GET", "http://example.test/example?config=cfg", nil)
					r.Header.Set("Origin", "https://example.test")
					r.Header.Set("Sec-WebSocket-Protocol", Protocol+", bearer."+signed(t, c))
					_, status := v.Authorize(r, "example", "wepp", service)
					if status != tc.status {
						t.Fatalf("status=%d want=%d", status, tc.status)
					}
				})
			}
		})
	}
}

func TestTransportAndOutage(t *testing.T) {
	m := miniredis.RunT(t)
	key := filepath.Join(t.TempDir(), "key")
	os.WriteFile(key, []byte("fixture-key"), 0600)
	v, err := New(key, &redis.Options{Addr: m.Addr()}, []string{"https://example.test"})
	if err != nil {
		t.Fatal(err)
	}
	defer v.Close()
	v.sessions.Set(context.Background(), "auth:session:run:example:sid", "1", time.Hour)
	token := signed(t, claimsFor("status"))
	for _, tc := range []struct {
		name, origin, query, protocol string
		want                          int
	}{
		{"missing origin", "", "config=cfg", Protocol + ", bearer." + token, 403},
		{"hostile origin", "https://hostile.test", "config=cfg", Protocol + ", bearer." + token, 403},
		{"missing token", "https://example.test", "config=cfg", Protocol, 401},
		{"duplicate token", "https://example.test", "config=cfg", Protocol + ", bearer." + token + ", bearer." + token, 401},
		{"duplicate config", "https://example.test", "config=cfg&config=cfg", Protocol + ", bearer." + token, 400},
		{"forged", "https://example.test", "config=cfg", Protocol + ", bearer." + token[:len(token)-4] + "aaaa", 401},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest("GET", "http://example.test/example?"+tc.query, nil)
			r.Header.Set("Origin", tc.origin)
			r.Header.Set("Sec-WebSocket-Protocol", tc.protocol)
			_, status := v.Authorize(r, "example", "wepp", "status")
			if status != tc.want {
				t.Fatalf("status=%d", status)
			}
		})
	}
	m.Close()
	r := httptest.NewRequest("GET", "http://example.test/example?config=cfg", nil)
	r.Header.Set("Origin", "https://example.test")
	r.Header.Set("Sec-WebSocket-Protocol", Protocol+", bearer."+token)
	if _, status := v.Authorize(r, "example", "wepp", "status"); status != 503 {
		t.Fatalf("outage status=%d", status)
	}
}

func TestStrictClaimsRotationAndOperation(t *testing.T) {
	m := miniredis.RunT(t)
	key := filepath.Join(t.TempDir(), "key")
	os.WriteFile(key, []byte("new-key,fixture-key"), 0600)
	v, err := New(key, &redis.Options{Addr: m.Addr()}, []string{"https://example.test"})
	if err != nil {
		t.Fatal(err)
	}
	defer v.Close()
	v.sessions.Set(context.Background(), "auth:session:run:example:sid", "1", time.Hour)
	check := func(token, channel, service string, want int) {
		t.Helper()
		r := httptest.NewRequest("GET", "http://example.test/example?config=cfg", nil)
		r.Header.Set("Origin", "https://example.test")
		r.Header.Set("Sec-WebSocket-Protocol", Protocol+", bearer."+token)
		_, status := v.Authorize(r, "example", channel, service)
		if status != want {
			t.Fatalf("status=%d want=%d", status, want)
		}
	}
	check(signed(t, claimsFor("status")), "wepp", "status", 0)
	for _, field := range []string{"session_id", "jti", "sub", "iat", "nbf", "exp"} {
		c := claimsFor("status")
		delete(c, field)
		check(signed(t, c), "wepp", "status", 401)
		c = claimsFor("status")
		c[field] = []string{"invalid"}
		check(signed(t, c), "wepp", "status", 401)
	}
	c := claimsFor("status")
	c["operation"] = "run-sync"
	c["job_id"] = "job"
	c["channel"] = "run_sync"
	check(signed(t, c), "run_sync", "status", 0)
	check(signed(t, c), "command", "status", 403)
	c = claimsFor("preflight")
	c["operation"] = "run-sync"
	c["job_id"] = "job"
	c["channel"] = "run_sync"
	check(signed(t, c), "", "preflight", 403)
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS384, claimsFor("status")).SignedString([]byte("fixture-key"))
	if err != nil {
		t.Fatal(err)
	}
	check(token, "wepp", "status", 401)
	// Use the library signer over deliberately ambiguous JSON (no custom cryptography).
	for _, duplicateHeader := range []bool{false, true} {
		raw, _ := json.Marshal(claimsFor("status"))
		header := `{"alg":"HS256","typ":"JWT"}`
		if duplicateHeader {
			header = `{"alg":"HS256","alg":"HS256","typ":"JWT"}`
		} else {
			raw = append([]byte(`{"runid":"other",`), raw[1:]...)
		}
		input := base64.RawURLEncoding.EncodeToString([]byte(header)) + "." + base64.RawURLEncoding.EncodeToString(raw)
		sig, err := jwt.SigningMethodHS256.Sign(input, []byte("fixture-key"))
		if err != nil {
			t.Fatal(err)
		}
		check(input+"."+base64.RawURLEncoding.EncodeToString(sig), "wepp", "status", 401)
	}
}
