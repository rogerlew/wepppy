package config

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	clearPreflightEnv(t)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.ListenAddr != defaultListenAddr {
		t.Fatalf("ListenAddr = %s, want %s", cfg.ListenAddr, defaultListenAddr)
	}
	if cfg.RedisEndpoint != defaultRedisEndpoint {
		t.Fatalf("RedisEndpoint = %s, want %s", cfg.RedisEndpoint, defaultRedisEndpoint)
	}
	if cfg.PingInterval != defaultPingInterval {
		t.Fatalf("PingInterval = %s, want %s", cfg.PingInterval, defaultPingInterval)
	}
	if cfg.PongTimeout != defaultPongTimeout {
		t.Fatalf("PongTimeout = %s, want %s", cfg.PongTimeout, defaultPongTimeout)
	}
	if cfg.WriteTimeout != defaultWriteTimeout {
		t.Fatalf("WriteTimeout = %s, want %s", cfg.WriteTimeout, defaultWriteTimeout)
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
		t.Fatalf("MetricsEnabled = %t, want false", cfg.MetricsEnabled)
	}
	if cfg.MaxMessageSize != defaultMaxMessageSize {
		t.Fatalf("MaxMessageSize = %d, want %d", cfg.MaxMessageSize, defaultMaxMessageSize)
	}
	if cfg.AllowedOrigins != nil {
		t.Fatalf("AllowedOrigins = %v, want nil", cfg.AllowedOrigins)
	}
}

func TestLoadEnvironmentOverrides(t *testing.T) {
	clearPreflightEnv(t)

	t.Setenv("PREFLIGHT_LISTEN_ADDR", "127.0.0.1:9101")
	t.Setenv("PREFLIGHT_REDIS_URL", "redis://redis:6380/4")
	t.Setenv("PREFLIGHT_PING_INTERVAL", "150ms")
	t.Setenv("PREFLIGHT_PONG_TIMEOUT", "2s")
	t.Setenv("PREFLIGHT_WRITE_TIMEOUT", "750ms")
	t.Setenv("PREFLIGHT_REDIS_REQUEST_TIMEOUT", "350ms")
	t.Setenv("PREFLIGHT_REDIS_RETRY_BASE", "200ms")
	t.Setenv("PREFLIGHT_REDIS_RETRY_MAX", "3s")
	t.Setenv("PREFLIGHT_REDIS_MAX_RETRIES", "11")
	t.Setenv("PREFLIGHT_LOG_LEVEL", "debug")
	t.Setenv("PREFLIGHT_ALLOWED_ORIGINS", "https://example.com, https://foo.test")
	t.Setenv("PREFLIGHT_METRICS_ENABLED", "true")
	t.Setenv("PREFLIGHT_MAX_MESSAGE_SIZE", "2048")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.ListenAddr != "127.0.0.1:9101" {
		t.Fatalf("ListenAddr = %s, want 127.0.0.1:9101", cfg.ListenAddr)
	}
	if cfg.RedisEndpoint != "redis://redis:6380/4" {
		t.Fatalf("RedisEndpoint = %s, want redis://redis:6380/4", cfg.RedisEndpoint)
	}
	if cfg.PingInterval != 150*time.Millisecond {
		t.Fatalf("PingInterval = %s, want 150ms", cfg.PingInterval)
	}
	if cfg.PongTimeout != 2*time.Second {
		t.Fatalf("PongTimeout = %s, want 2s", cfg.PongTimeout)
	}
	if cfg.WriteTimeout != 750*time.Millisecond {
		t.Fatalf("WriteTimeout = %s, want 750ms", cfg.WriteTimeout)
	}
	if cfg.RedisRequestTimeout != 350*time.Millisecond {
		t.Fatalf("RedisRequestTimeout = %s, want 350ms", cfg.RedisRequestTimeout)
	}
	if cfg.RedisRetryBase != 200*time.Millisecond {
		t.Fatalf("RedisRetryBase = %s, want 200ms", cfg.RedisRetryBase)
	}
	if cfg.RedisRetryMax != 3*time.Second {
		t.Fatalf("RedisRetryMax = %s, want 3s", cfg.RedisRetryMax)
	}
	if cfg.RedisMaxRetries != 11 {
		t.Fatalf("RedisMaxRetries = %d, want 11", cfg.RedisMaxRetries)
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
	if cfg.MaxMessageSize != 2048 {
		t.Fatalf("MaxMessageSize = %d, want 2048", cfg.MaxMessageSize)
	}
}

func TestLoadRedisEndpointFallbackWithPassword(t *testing.T) {
	clearPreflightEnv(t)

	t.Setenv("REDIS_URL", "redis://redis:6379/0")
	t.Setenv("REDIS_PASSWORD", "sekret")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.RedisEndpoint != "redis://redis:6379/0" {
		t.Fatalf("RedisEndpoint = %s, want redis://redis:6379/0", cfg.RedisEndpoint)
	}
}

func TestLoadPreflightRedisEndpointInjectsPassword(t *testing.T) {
	clearPreflightEnv(t)

	t.Setenv("PREFLIGHT_REDIS_URL", "redis://redis:6379/0")
	t.Setenv("REDIS_PASSWORD", "sekret")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.RedisEndpoint != "redis://redis:6379/0" {
		t.Fatalf("RedisEndpoint = %s, want redis://redis:6379/0", cfg.RedisEndpoint)
	}
}

func TestLoadRedisEndpointFallbackWithPasswordFile(t *testing.T) {
	clearPreflightEnv(t)

	secretPath := filepath.Join(t.TempDir(), "redis_password")
	if err := os.WriteFile(secretPath, []byte("sekret\n"), 0600); err != nil {
		t.Fatalf("WriteFile() returned error: %v", err)
	}

	t.Setenv("REDIS_URL", "redis://redis:6379/0")
	t.Setenv("REDIS_PASSWORD_FILE", secretPath)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.RedisEndpoint != "redis://redis:6379/0" {
		t.Fatalf("RedisEndpoint = %s, want redis://redis:6379/0", cfg.RedisEndpoint)
	}
}

func TestLoadPreflightRedisEndpointInjectsPasswordFromFile(t *testing.T) {
	clearPreflightEnv(t)

	secretPath := filepath.Join(t.TempDir(), "redis_password")
	if err := os.WriteFile(secretPath, []byte("sekret\n"), 0600); err != nil {
		t.Fatalf("WriteFile() returned error: %v", err)
	}

	t.Setenv("PREFLIGHT_REDIS_URL", "redis://redis:6379/0")
	t.Setenv("PREFLIGHT_REDIS_PASSWORD_FILE", secretPath)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.RedisEndpoint != "redis://redis:6379/0" {
		t.Fatalf("RedisEndpoint = %s, want redis://redis:6379/0", cfg.RedisEndpoint)
	}
}

func TestLoadErrorsWhenRedisPasswordFileIsEmpty(t *testing.T) {
	clearPreflightEnv(t)

	secretPath := filepath.Join(t.TempDir(), "redis_password")
	if err := os.WriteFile(secretPath, []byte("\n"), 0600); err != nil {
		t.Fatalf("WriteFile() returned error: %v", err)
	}

	t.Setenv("REDIS_PASSWORD_FILE", secretPath)

	if _, err := Load(); err == nil {
		t.Fatalf("Load() expected error for empty REDIS_PASSWORD_FILE, got nil")
	}
}

func TestStringRedactsRedisPassword(t *testing.T) {
	clearPreflightEnv(t)
	t.Setenv("REDIS_URL", "redis://:sekret@redis:6379/2")
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(fmt.Sprintf("%v %+v %#v %v", cfg, cfg, cfg, cfg.RedisOptions), "sekret") {
		t.Fatal("config representation leaked credential")
	}
	_, password := cfg.RedisOptions.CredentialsProvider()
	if password != "sekret" {
		t.Fatal("credential was lost")
	}
}

func clearPreflightEnv(t *testing.T) {
	t.Helper()
	for _, kv := range os.Environ() {
		if !strings.HasPrefix(kv, "PREFLIGHT_") {
			continue
		}
		key := kv[:strings.Index(kv, "=")]
		os.Unsetenv(key)
	}
	for _, key := range []string{"REDIS_URL", "REDIS_PASSWORD", "REDIS_HOST", "REDIS_PORT"} {
		os.Unsetenv(key)
	}
	for _, key := range []string{"REDIS_PASSWORD_FILE", "PREFLIGHT_REDIS_PASSWORD_FILE"} {
		os.Unsetenv(key)
	}
}

func TestPasswordFileFraming(t *testing.T) {
	clearPreflightEnv(t)
	path := filepath.Join(t.TempDir(), "password")
	t.Setenv("REDIS_PASSWORD_FILE", path)
	for _, value := range []string{"", "\n", " secret\n", "secret \n", "secret\r\n", "a\x00b", "\u00a0secret\n", "secret\u2003\n", "\x1csecret", "secret\x1f", string([]byte{0xff})} {
		if err := os.WriteFile(path, []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
		if _, err := Load(); err == nil {
			t.Fatal("invalid secret file accepted")
		}
	}
	if err := os.WriteFile(path, []byte("é 🔒:@ %\n\n"), 0600); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load()
	if err != nil {
		t.Fatal(err)
	}
	_, password := cfg.RedisOptions.CredentialsProvider()
	if password != "é 🔒:@ %" {
		t.Fatal("valid UTF-8 credential changed")
	}
}

func TestMalformedHostConfiguration(t *testing.T) {
	clearPreflightEnv(t)
	for _, host := range []string{"user@cache", "cache?password=canary", "cache/path", "cache host"} {
		t.Setenv("REDIS_HOST", host)
		if _, err := Load(); err == nil {
			t.Fatal("invalid host accepted")
		}
	}
}
