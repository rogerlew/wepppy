//go:build integration

package server

import (
	"context"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	miniredis "github.com/alicebob/miniredis/v2"
	"github.com/golang-jwt/jwt/v5"
	"github.com/rogerlew/wepppy/services/status2/internal/config"
	"nhooyr.io/websocket"
)

func streamFixture(t *testing.T) (*Server, *httptest.Server, *miniredis.Miniredis) {
	t.Helper()
	m := miniredis.RunT(t)
	key := filepath.Join(t.TempDir(), "key")
	if err := os.WriteFile(key, []byte("fixture-key"), 0600); err != nil {
		t.Fatal(err)
	}
	cfg := config.Config{RedisEndpoint: "redis://" + m.Addr() + "/2", SigningKeyFile: key, AllowedOrigins: []string{"https://example.test"},
		PingInterval: time.Second, PongTimeout: 5 * time.Second, WriteTimeout: time.Second, RedisRequestTimeout: time.Second,
		RedisRetryBase: time.Millisecond, RedisRetryMax: time.Second, RedisMaxRetries: 1, MaxMessageSize: 65536}
	srv, err := New(cfg, slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { srv.Close() })
	server := httptest.NewServer(srv.Handler())
	t.Cleanup(server.Close)
	m.Select(11)
	m.Set("auth:session:run:example:sid", "1")
	m.Select(2)
	return srv, server, m
}
func serviceToken(t *testing.T, run string, ttl int64) string {
	t.Helper()
	now := time.Now().Unix()
	c := jwt.MapClaims{"iss": "weppcloud-stream", "aud": "wepp-status", "token_class": "session", "stream": "status", "scope": "status:read",
		"runid": run, "config": "cfg", "sub": "sid", "session_id": "sid", "jti": "jti", "iat": now, "nbf": now, "exp": now + ttl}
	token, err := jwt.NewWithClaims(jwt.SigningMethodHS256, c).SignedString([]byte("fixture-key"))
	if err != nil {
		t.Fatal("signing failed")
	}
	return token
}
func TestStreamUpgradeDeniesBeforeRunRedis(t *testing.T) {
	_, server, m := streamFixture(t)
	for _, tc := range []struct{ name, origin, token string }{
		{"missing", "https://example.test", ""},
		{"cross-run", "https://example.test", serviceToken(t, "other", 300)},
		{"hostile", "https://hostile.test", serviceToken(t, "example", 300)},
	} {
		t.Run(tc.name, func(t *testing.T) {
			before := m.CommandCount()
			req, _ := http.NewRequest("GET", server.URL+"/example:wepp?config=cfg", nil)
			req.Header.Set("Origin", tc.origin)
			if tc.token != "" {
				req.Header.Set("Sec-WebSocket-Protocol", "wepp-stream.v1, bearer."+tc.token)
			}
			response, err := http.DefaultClient.Do(req)
			if err != nil {
				t.Fatal("request failed")
			}
			response.Body.Close()
			if response.StatusCode != 401 && response.StatusCode != 403 {
				t.Fatalf("unexpected status %d", response.StatusCode)
			}
			if m.CommandCount() != before {
				t.Fatal("denied handshake touched Redis")
			}
		})
	}
}
func TestStreamExpiryAndSelectedProtocol(t *testing.T) {
	srv, server, m := streamFixture(t)
	_ = srv
	_ = m
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	conn, response, err := websocket.Dial(ctx, "ws"+strings.TrimPrefix(server.URL, "http")+"/example:wepp?config=cfg", &websocket.DialOptions{
		HTTPHeader: http.Header{"Origin": []string{"https://example.test"}}, Subprotocols: []string{"wepp-stream.v1", "bearer." + serviceToken(t, "example", 2)}})
	if err != nil {
		t.Fatal("authorized handshake failed")
	}
	defer conn.CloseNow()
	if response.StatusCode != 101 || conn.Subprotocol() != "wepp-stream.v1" {
		t.Fatal("incorrect negotiated protocol")
	}
	for {
		_, data, err := conn.Read(ctx)
		if err != nil {
			if websocket.CloseStatus(err) != 4001 {
				t.Fatalf("expiry status=%d", websocket.CloseStatus(err))
			}
			break
		}
		if strings.Contains(string(data), `"type":"hangup"`) {
			t.Fatal("expiry sent terminal hangup")
		}
		if strings.Contains(string(data), `"type":"ping"`) {
			conn.Write(ctx, websocket.MessageText, []byte(`{"type":"pong"}`))
		}
	}
}
