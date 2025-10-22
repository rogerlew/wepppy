package server

import (
	"context"
	"math/rand"
	"testing"
	"time"

	"github.com/rogerlew/wepppy/services/status2/internal/config"
)

func TestRedisBackoffWithinBounds(t *testing.T) {
	srv := &Server{
		cfg: config.Config{
			RedisRetryMax: 1600 * time.Millisecond,
		},
	}

	conn := &connection{
		srv:  srv,
		rand: rand.New(rand.NewSource(42)),
	}

	base := 100 * time.Millisecond

	if got := conn.redisBackoff(0, base); got != base {
		t.Fatalf("attempt=0 got=%s want=%s", got, base)
	}

	got := conn.redisBackoff(3, base)
	maxBackoff := base * time.Duration(1<<uint(3-1))
	if maxBackoff > srv.cfg.RedisRetryMax {
		maxBackoff = srv.cfg.RedisRetryMax
	}
	if got < base || got > maxBackoff {
		t.Fatalf("attempt=3 got=%s want between %s and %s", got, base, maxBackoff)
	}

	// When calculated backoff exceeds the configured maximum, ensure we respect the cap.
	got = conn.redisBackoff(10, base)
	if got > srv.cfg.RedisRetryMax {
		t.Fatalf("attempt=10 got=%s exceeds max %s", got, srv.cfg.RedisRetryMax)
	}
	if got < base {
		t.Fatalf("attempt=10 got=%s below base %s", got, base)
	}
}

func TestShouldAbortHonorsMaxRetries(t *testing.T) {
	srv := &Server{
		cfg: config.Config{
			RedisMaxRetries: 3,
		},
	}
	conn := &connection{srv: srv}

	if abort := conn.shouldAbort(2); abort {
		t.Fatalf("shouldAbort(2) = true, want false")
	}
	if abort := conn.shouldAbort(3); !abort {
		t.Fatalf("shouldAbort(3) = false, want true")
	}
	if abort := conn.shouldAbort(5); !abort {
		t.Fatalf("shouldAbort(5) = false, want true when MaxRetries reached")
	}
}

func TestShouldAbortWhenUnlimited(t *testing.T) {
	conn := &connection{
		srv: &Server{
			cfg: config.Config{RedisMaxRetries: 0},
		},
	}

	if abort := conn.shouldAbort(100); abort {
		t.Fatalf("shouldAbort with unlimited retries returned true")
	}
}

func TestRedisRequestContext(t *testing.T) {
	conn := &connection{
		srv: &Server{
			cfg: config.Config{RedisRequestTimeout: 0},
		},
	}

	parent := context.Background()
	ctx, cancel := conn.redisRequestContext(parent)
	defer cancel()
	if ctx != parent {
		t.Fatalf("expected parent context when timeout <= 0")
	}

	timeoutConn := &connection{
		srv: &Server{
			cfg: config.Config{RedisRequestTimeout: 100 * time.Millisecond},
		},
	}

	child, cancel := timeoutConn.redisRequestContext(parent)
	defer cancel()
	deadline, ok := child.Deadline()
	if !ok {
		t.Fatalf("expected deadline to be set on child context")
	}
	now := time.Now()
	if deadline.Before(now) || deadline.After(now.Add(100*time.Millisecond+50*time.Millisecond)) {
		t.Fatalf("deadline not within expected window, got %v", deadline)
	}
}
