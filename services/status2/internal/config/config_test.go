package config

import (
	"log/slog"
	"os"
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	clearStatusEnv(t)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.ListenAddr != defaultListenAddr {
		t.Fatalf("ListenAddr = %s, want %s", cfg.ListenAddr, defaultListenAddr)
	}
	if cfg.RedisURL != defaultRedisURL {
		t.Fatalf("RedisURL = %s, want %s", cfg.RedisURL, defaultRedisURL)
	}
	if cfg.PingInterval != defaultPingInterval {
		t.Fatalf("PingInterval = %s, want %s", cfg.PingInterval, defaultPingInterval)
	}
	if cfg.PongTimeout != defaultPongTimeout {
		t.Fatalf("PongTimeout = %s, want %s", cfg.PongTimeout, defaultPongTimeout)
	}
	if cfg.RedisRequestTimeout != defaultRedisRequestTimout {
		t.Fatalf("RedisRequestTimeout = %s, want %s", cfg.RedisRequestTimeout, defaultRedisRequestTimout)
	}
	if cfg.RedisRetryBase != defaultRedisRetryBase {
		t.Fatalf("RedisRetryBase = %s, want %s", cfg.RedisRetryBase, defaultRedisRetryBase)
	}
	if cfg.RedisRetryMax != defaultRedisRetryMax {
		t.Fatalf("RedisRetryMax = %s, want %s", cfg.RedisRetryMax, defaultRedisRetryMax)
	}
	if cfg.RedisMaxRetries != defaultRedisMaxRetries {
		t.Fatalf("RedisMaxRetries = %d, want %d", cfg.RedisMaxRetries, defaultRedisMaxRetries)
	}
	if cfg.LogLevel != defaultLogLevel {
		t.Fatalf("LogLevel = %s, want %s", cfg.LogLevel, defaultLogLevel)
	}
	if cfg.MetricsEnabled {
		t.Fatalf("MetricsEnabled = true, want false")
	}
	if cfg.MaxMessageSize != defaultMaxMessageSize {
		t.Fatalf("MaxMessageSize = %d, want %d", cfg.MaxMessageSize, defaultMaxMessageSize)
	}
	if cfg.AllowedOrigins != nil {
		t.Fatalf("AllowedOrigins = %v, want nil", cfg.AllowedOrigins)
	}
}

func TestLoadEnvironmentOverrides(t *testing.T) {
	clearStatusEnv(t)

	t.Setenv("STATUS_LISTEN_ADDR", "127.0.0.1:9100")
	t.Setenv("STATUS_REDIS_URL", "redis://redis:6379/15")
	t.Setenv("STATUS_PING_INTERVAL", "150ms")
	t.Setenv("STATUS_PONG_TIMEOUT", "2s")
	t.Setenv("STATUS_WRITE_TIMEOUT", "500ms")
	t.Setenv("STATUS_REDIS_REQUEST_TIMEOUT", "250ms")
	t.Setenv("STATUS_REDIS_RETRY_BASE", "200ms")
	t.Setenv("STATUS_REDIS_RETRY_MAX", "3s")
	t.Setenv("STATUS_REDIS_MAX_RETRIES", "9")
	t.Setenv("STATUS_LOG_LEVEL", "debug")
	t.Setenv("STATUS_ALLOWED_ORIGINS", "https://example.com, https://foo.test")
	t.Setenv("STATUS_METRICS_ENABLED", "true")
	t.Setenv("STATUS_MAX_MESSAGE_SIZE", "1024")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.ListenAddr != "127.0.0.1:9100" {
		t.Fatalf("ListenAddr = %s, want 127.0.0.1:9100", cfg.ListenAddr)
	}
	if cfg.RedisURL != "redis://redis:6379/15" {
		t.Fatalf("RedisURL = %s, want redis://redis:6379/15", cfg.RedisURL)
	}
	if cfg.PingInterval != 150*time.Millisecond {
		t.Fatalf("PingInterval = %s, want 150ms", cfg.PingInterval)
	}
	if cfg.PongTimeout != 2*time.Second {
		t.Fatalf("PongTimeout = %s, want 2s", cfg.PongTimeout)
	}
	if cfg.WriteTimeout != 500*time.Millisecond {
		t.Fatalf("WriteTimeout = %s, want 500ms", cfg.WriteTimeout)
	}
	if cfg.RedisRequestTimeout != 250*time.Millisecond {
		t.Fatalf("RedisRequestTimeout = %s, want 250ms", cfg.RedisRequestTimeout)
	}
	if cfg.RedisRetryBase != 200*time.Millisecond {
		t.Fatalf("RedisRetryBase = %s, want 200ms", cfg.RedisRetryBase)
	}
	if cfg.RedisRetryMax != 3*time.Second {
		t.Fatalf("RedisRetryMax = %s, want 3s", cfg.RedisRetryMax)
	}
	if cfg.RedisMaxRetries != 9 {
		t.Fatalf("RedisMaxRetries = %d, want 9", cfg.RedisMaxRetries)
	}
	if cfg.LogLevel != slog.LevelDebug {
		t.Fatalf("LogLevel = %s, want %s", cfg.LogLevel, slog.LevelDebug)
	}
	expectedOrigins := []string{"https://example.com", "https://foo.test"}
	if len(cfg.AllowedOrigins) != len(expectedOrigins) {
		t.Fatalf("AllowedOrigins length = %d, want %d", len(cfg.AllowedOrigins), len(expectedOrigins))
	}
	for i, origin := range expectedOrigins {
		if cfg.AllowedOrigins[i] != origin {
			t.Fatalf("AllowedOrigins[%d] = %s, want %s", i, cfg.AllowedOrigins[i], origin)
		}
	}
	if !cfg.MetricsEnabled {
		t.Fatalf("MetricsEnabled = false, want true")
	}
	if cfg.MaxMessageSize != 1024 {
		t.Fatalf("MaxMessageSize = %d, want 1024", cfg.MaxMessageSize)
	}
}

func clearStatusEnv(t *testing.T) {
	t.Helper()
	for _, env := range os.Environ() {
		if len(env) == 0 {
			continue
		}
		if env[0] != 'S' {
			continue
		}
		if len(env) < len("STATUS_") || env[:len("STATUS_")] != "STATUS_" {
			continue
		}
		key := env[:findEquals(env)]
		os.Unsetenv(key)
	}
}

func findEquals(s string) int {
	for i := range s {
		if s[i] == '=' {
			return i
		}
	}
	return len(s)
}
