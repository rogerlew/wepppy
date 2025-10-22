//go:build integration

package server

import (
	"context"
	"testing"
	"time"

	miniredis "github.com/alicebob/miniredis/v2"
	"github.com/redis/go-redis/v9"

	"github.com/rogerlew/wepppy/services/preflight2/internal/config"
)

func TestRedisLoopPublishesUpdates(t *testing.T) {
	m := miniredis.RunT(t)
	defer m.Close()

	client := redis.NewClient(&redis.Options{Addr: m.Addr(), DB: 0})
	defer client.Close()

	runID := "integration"
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
			RedisRetryBase:      10 * time.Millisecond,
			RedisRetryMax:       100 * time.Millisecond,
			RedisMaxRetries:     3,
			WriteTimeout:        time.Second,
		},
		redis: client,
	}

	fake := &fakeConn{}
	conn := newConnection(srv, nil, runID, fake)

	if err := conn.pushUpdate(context.Background()); err != nil {
		t.Fatalf("initial pushUpdate: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan error, 1)
	go func() {
		done <- conn.redisLoop(ctx)
	}()

	time.Sleep(50 * time.Millisecond)

	if err := client.HSet(context.Background(), runID, map[string]string{
		"timestamps:build_landuse": "10",
	}).Err(); err != nil {
		t.Fatalf("update redis: %v", err)
	}
	if err := client.Publish(context.Background(), "__keyspace@0__:"+runID, "hset").Err(); err != nil {
		t.Fatalf("publish notification: %v", err)
	}

	deadline := time.Now().Add(5 * time.Second)
	for len(fake.messages) < 2 && time.Now().Before(deadline) {
		time.Sleep(20 * time.Millisecond)
	}

	cancel()
	select {
	case <-done:
	case <-time.After(2 * time.Second):
		t.Fatalf("redisLoop did not exit after cancel")
	}

	if len(fake.messages) < 2 {
		t.Fatalf("expected at least 2 messages (initial + update), got %d", len(fake.messages))
	}
}
