package server

import (
	"context"
	"sync"
	"testing"
	"time"

	miniredis "github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"
	"nhooyr.io/websocket"

	"github.com/rogerlew/wepppy/services/preflight2/internal/config"
)

func TestRedisBackoffHonoursBounds(t *testing.T) {
	srv := &Server{
		cfg: config.Config{
			RedisRetryMax: 1200 * time.Millisecond,
		},
	}
	conn := &connection{
		srv: srv,
	}

	base := 100 * time.Millisecond
	if got := conn.redisBackoff(0, base); got != base {
		t.Fatalf("attempt=0 got=%s want=%s", got, base)
	}

	attempt := 4
	got := conn.redisBackoff(attempt, base)
	wantMax := base * time.Duration(1<<uint(attempt-1))
	if wantMax > srv.cfg.RedisRetryMax {
		wantMax = srv.cfg.RedisRetryMax
	}
	if got < base || got > wantMax {
		t.Fatalf("attempt=%d got=%s, expected between %s and %s", attempt, got, base, wantMax)
	}

	got = conn.redisBackoff(10, base)
	if got > srv.cfg.RedisRetryMax {
		t.Fatalf("got=%s exceeds max=%s", got, srv.cfg.RedisRetryMax)
	}
	if got < base {
		t.Fatalf("got=%s below base=%s", got, base)
	}
}

func TestShouldAbortRespectsMaxRetries(t *testing.T) {
	conn := &connection{
		srv: &Server{
			cfg: config.Config{RedisMaxRetries: 3},
		},
	}

	if conn.shouldAbort(2) {
		t.Fatalf("shouldAbort(2) = true, want false")
	}
	if !conn.shouldAbort(3) {
		t.Fatalf("shouldAbort(3) = false, want true")
	}
}

func TestShouldAbortUnlimitedRetries(t *testing.T) {
	conn := &connection{
		srv: &Server{cfg: config.Config{RedisMaxRetries: 0}},
	}
	if conn.shouldAbort(999) {
		t.Fatalf("unbounded retries should never abort")
	}
}

func TestKeyspaceChannelMatchesDB(t *testing.T) {
	srv := &Server{redisDB: 2}
	channel := srv.keyspaceChannel("testrun")
	if channel != "__keyspace@2__:testrun" {
		t.Fatalf("channel = %s, want __keyspace@2__:testrun", channel)
	}
}

func TestPushUpdateWritesMessage(t *testing.T) {
	m := miniredis.RunT(t)
	defer m.Close()

	client := redis.NewClient(&redis.Options{Addr: m.Addr(), DB: 0})
	defer client.Close()

	runID := "testrun"
	if err := client.HSet(context.Background(), runID, map[string]string{
		"attrs:has_sbs":                 "true",
		"timestamps:build_channels":     "1",
		"timestamps:set_outlet":         "2",
		"timestamps:abstract_watershed": "3",
	}).Err(); err != nil {
		t.Fatalf("seed redis: %v", err)
	}

	srv := &Server{
		cfg: config.Config{
			RedisRequestTimeout: 500 * time.Millisecond,
			WriteTimeout:        time.Second,
		},
		redis: client,
	}

	fake := &fakeConn{}
	conn := newConnection(srv, nil, runID, fake)
	if err := conn.pushUpdate(context.Background()); err != nil {
		t.Fatalf("pushUpdate: %v", err)
	}
	if len(fake.messages) != 1 {
		t.Fatalf("expected 1 message, got %d", len(fake.messages))
	}
}

type fakeConn struct {
	messages [][]byte
	mu       sync.Mutex
}

func (f *fakeConn) Read(_ context.Context) (websocket.MessageType, []byte, error) {
	return websocket.MessageText, nil, context.Canceled
}

func (f *fakeConn) Write(_ context.Context, typ websocket.MessageType, data []byte) error {
	if typ != websocket.MessageText {
		return nil
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.messages = append(f.messages, append([]byte(nil), data...))
	return nil
}

func (f *fakeConn) Close(_ websocket.StatusCode, _ string) error {
	return nil
}

func (f *fakeConn) SetReadLimit(int64) {}
