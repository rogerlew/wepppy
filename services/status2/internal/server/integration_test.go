//go:build integration

package server

import (
	"context"
	"encoding/json"
	"io"
 "os"
 "path/filepath"
 "net/http"
	"log/slog"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	miniredis "github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"nhooyr.io/websocket"

	"github.com/rogerlew/wepppy/services/status2/internal/config"
	"github.com/rogerlew/wepppy/services/status2/internal/payload"
)

func TestStatusWebsocketFlow(t *testing.T) {
	m := miniredis.RunT(t)
	defer m.Close()

	key := filepath.Join(t.TempDir(), "key")
 os.WriteFile(key, []byte("fixture-key"), 0600)
 m.Select(11)
 m.Set("auth:session:run:testrun:sid", "1")
 m.Select(2)
 cfg := config.Config{
 SigningKeyFile: key,
		ListenAddr:          ":0",
		RedisURL:            "redis://" + m.Addr() + "/2",
		PingInterval:        time.Second,
		PongTimeout:         5 * time.Second,
		WriteTimeout:        time.Second,
		RedisRequestTimeout: 200 * time.Millisecond,
		RedisRetryBase:      10 * time.Millisecond,
		RedisRetryMax:       200 * time.Millisecond,
		RedisMaxRetries:     3,
		LogLevel:            slog.LevelInfo,
		AllowedOrigins:      []string{"https://example.test"},
		MetricsEnabled:      false,
		MaxMessageSize:      64 * 1024,
	}

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))

	srv, err := New(cfg, logger)
	if err != nil {
		t.Fatalf("New server: %v", err)
	}
	defer srv.Close()

	httpServer := httptest.NewServer(srv.Handler())
	defer httpServer.Close()

	wsURL := "ws" + strings.TrimPrefix(httpServer.URL, "http") + "/testrun:wepp?config=cfg"

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	conn, _, err := websocket.Dial(ctx, wsURL, &websocket.DialOptions{HTTPHeader: http.Header{"Origin": []string{"https://example.test"}}, Subprotocols: []string{"wepp-stream.v1", "bearer."+serviceToken(t,"testrun",300)}})
	if err != nil {
		t.Fatalf("websocket dial: %v", err)
	}
	defer conn.Close(websocket.StatusNormalClosure, "test complete")

	if err := conn.Write(ctx, websocket.MessageText, []byte(`{"type":"init"}`)); err != nil {
		t.Fatalf("sending init frame: %v", err)
	}

	statusCh := make(chan payload.StatusMessage, 1)
	errCh := make(chan error, 1)

	go func() {
		readCtx, readCancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer readCancel()
		for {
			messageType, data, err := conn.Read(readCtx)
			if err != nil {
				errCh <- err
				return
			}
			if messageType != websocket.MessageText {
				continue
			}

			var frame struct {
				Type string `json:"type"`
				Data string `json:"data,omitempty"`
			}
			if json.Unmarshal(data, &frame) != nil {
				continue
			}

			switch strings.ToLower(frame.Type) {
			case "ping":
				// Respond with pong to keep the connection alive.
				if writeErr := conn.Write(readCtx, websocket.MessageText, []byte(`{"type":"pong"}`)); writeErr != nil {
					errCh <- writeErr
					return
				}
			case "status":
				statusCh <- payload.StatusMessage{Type: frame.Type, Data: frame.Data}
				return
			}
		}
	}()

	redisClient := redis.NewClient(&redis.Options{
		Addr: m.Addr(),
		DB:   2,
	})
	defer redisClient.Close()

	const expected = "hello world"
	time.Sleep(50 * time.Millisecond)
	if err := redisClient.Publish(ctx, "testrun:wepp", expected).Err(); err != nil {
		t.Fatalf("redis publish: %v", err)
	}

	select {
	case msg := <-statusCh:
		if msg.Type != "status" {
			t.Fatalf("unexpected message type: %s", msg.Type)
		}
		if msg.Data != expected {
			t.Fatalf("message data = %q, want %q", msg.Data, expected)
		}
	case err := <-errCh:
		t.Fatalf("websocket loop error: %v", err)
	case <-time.After(5 * time.Second):
		t.Fatalf("timed out waiting for status message")
	}
}
