package streamauth

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"
)

func TestRedisCredentialsAndOptions(t *testing.T) {
	endpoint, opts, err := ParseRedisEndpoint("rediss://user:p%40ss@[::1]:6380/2?dial_timeout=2s", "p@ss")
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(endpoint, "@") || opts.DB != 2 || opts.DialTimeout != 2*time.Second || opts.TLSConfig == nil {
		t.Fatal("endpoint/options lost")
	}
	user, pass := opts.CredentialsProvider()
	if user != "user" || pass != "p@ss" {
		t.Fatal("credentials lost")
	}
	if strings.Contains(fmt.Sprintf("%+v %#v", opts, opts), "p@ss") {
		t.Fatal("credential leaked")
	}
	for _, raw := range []string{"redis://:url-canary@cache/2", "redis://cache/2?password=file-canary", "redis://bad:file-canary@[/2"} {
		_, _, err := ParseRedisEndpoint(raw, "file-canary")
		if err == nil || strings.Contains(err.Error(), "canary") {
			t.Fatal("unsafe failure")
		}
	}
}

// Opt-in direct AUTH boundary. The acceptance harness supplies an isolated Redis.
func TestRealRedisTransport(t *testing.T) {
	addr := os.Getenv("REDIS_TRANSPORT_TEST_ADDR")
	if addr == "" {
		t.Skip("isolated Redis not configured")
	}
	raw, err := os.ReadFile(os.Getenv("REDIS_TRANSPORT_TEST_PASSWORD_FILE"))
	if err != nil {
		t.Fatal("password file unavailable")
	}
	_, opts, err := ParseRedisEndpoint("redis://"+addr+"/2", strings.TrimRight(string(raw), "\n"))
	if err != nil {
		t.Fatal(err)
	}
	client := redis.NewClient(opts)
	defer client.Close()
	if err := client.Ping(context.Background()).Err(); err != nil {
		t.Fatal(err)
	}
	key := filepath.Join(t.TempDir(), "signing")
	if err := os.WriteFile(key, []byte("fixture-key"), 0600); err != nil {
		t.Fatal(err)
	}
	validator, err := New(key, opts, []string{"https://example.test"})
	if err != nil {
		t.Fatal(err)
	}
	defer validator.Close()
	if validator.sessions.Options().DB != 11 || validator.revoked.Options().DB != 0 || opts.DB != 2 {
		t.Fatal("database isolation lost")
	}
	for _, conn := range []*redis.Client{validator.sessions, validator.revoked} {
		if err := conn.Ping(context.Background()).Err(); err != nil {
			t.Fatal(err)
		}
	}
	for _, password := range []string{"", "wrong-transport-password"} {
		_, wrong, err := ParseRedisEndpoint("redis://"+addr+"/2", password)
		if err != nil {
			t.Fatal(err)
		}
		conn := redis.NewClient(wrong)
		err = conn.Ping(context.Background()).Err()
		conn.Close()
		if err == nil {
			t.Fatal("invalid credential accepted")
		}
	}
}

func TestMalformedRedisEndpoints(t *testing.T) {
	for _, raw := range []string{"redis:///2", "redis://localhost:0/2", "redis://localhost:99999/2", "redis://:@localhost/2", "redis://localhost/2?ssl_password=canary"} {
		if _, _, err := ParseRedisEndpoint(raw, ""); err == nil {
			t.Fatalf("malformed endpoint accepted")
		}
	}
}
