package config

import (
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	ListenAddr          string
	RedisURL            string
	PingInterval        time.Duration
	PongTimeout         time.Duration
	WriteTimeout        time.Duration
	RedisRequestTimeout time.Duration
	RedisMaxRetries     int
	RedisRetryBase      time.Duration
	RedisRetryMax       time.Duration
	LogLevel            slog.Level
	AllowedOrigins      []string
	MetricsEnabled      bool
	MaxMessageSize      int64
}

const (
	envPrefix                 = "STATUS_"
	defaultListenAddr         = ":9002"
	defaultRedisURL           = "redis://localhost:6379/2"
	defaultPingInterval       = 5 * time.Second
	defaultPongTimeout        = 15 * time.Second
	defaultWriteTimeout       = 2 * time.Second
	defaultRedisRequestTimout = time.Second
	defaultRedisRetryBase     = time.Second
	defaultRedisRetryMax      = 30 * time.Second
	defaultRedisMaxRetries    = 5
	defaultLogLevel           = slog.LevelInfo
	defaultMaxMessageSize     = 64 * 1024
)

func Load() (Config, error) {
	cfg := Config{
		ListenAddr:          getEnv("LISTEN_ADDR", defaultListenAddr),
		RedisURL:            getEnv("REDIS_URL", defaultRedisURL),
		PingInterval:        getDurationEnv("PING_INTERVAL", defaultPingInterval),
		PongTimeout:         getDurationEnv("PONG_TIMEOUT", defaultPongTimeout),
		WriteTimeout:        getDurationEnv("WRITE_TIMEOUT", defaultWriteTimeout),
		RedisRequestTimeout: getDurationEnv("REDIS_REQUEST_TIMEOUT", defaultRedisRequestTimout),
		RedisRetryBase:      getDurationEnv("REDIS_RETRY_BASE", defaultRedisRetryBase),
		RedisRetryMax:       getDurationEnv("REDIS_RETRY_MAX", defaultRedisRetryMax),
		RedisMaxRetries:     getIntEnv("REDIS_MAX_RETRIES", defaultRedisMaxRetries),
		LogLevel:            parseLogLevel(getEnv("LOG_LEVEL", "")),
		AllowedOrigins:      parseList(os.Getenv(envKey("ALLOWED_ORIGINS"))),
		MetricsEnabled:      getBoolEnv("METRICS_ENABLED", false),
		MaxMessageSize:      int64(getIntEnv("MAX_MESSAGE_SIZE", int(defaultMaxMessageSize))),
	}

	if cfg.RedisRetryBase <= 0 {
		cfg.RedisRetryBase = defaultRedisRetryBase
	}
	if cfg.RedisRetryMax <= 0 {
		cfg.RedisRetryMax = defaultRedisRetryMax
	}
	if cfg.LogLevel == 0 && getEnv("LOG_LEVEL", "") == "" {
		cfg.LogLevel = defaultLogLevel
	}
	if cfg.MaxMessageSize <= 0 {
		cfg.MaxMessageSize = defaultMaxMessageSize
	}
	return cfg, nil
}

func envKey(key string) string {
	return envPrefix + key
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(envKey(key)); v != "" {
		return v
	}
	return fallback
}

func getDurationEnv(key string, fallback time.Duration) time.Duration {
	raw := os.Getenv(envKey(key))
	if raw == "" {
		return fallback
	}
	d, err := time.ParseDuration(raw)
	if err != nil {
		return fallback
	}
	return d
}

func getIntEnv(key string, fallback int) int {
	raw := os.Getenv(envKey(key))
	if raw == "" {
		return fallback
	}
	v, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return v
}

func getBoolEnv(key string, fallback bool) bool {
	raw := os.Getenv(envKey(key))
	if raw == "" {
		return fallback
	}
	value, err := strconv.ParseBool(raw)
	if err != nil {
		return fallback
	}
	return value
}

func parseList(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

func parseLogLevel(raw string) slog.Level {
	raw = strings.TrimSpace(strings.ToLower(raw))
	switch raw {
	case "debug":
		return slog.LevelDebug
	case "info", "":
		return slog.LevelInfo
	case "warn", "warning":
		return slog.LevelWarn
	case "error":
		return slog.LevelError
	default:
		return defaultLogLevel
	}
}

func (c Config) String() string {
	origins := "any"
	if len(c.AllowedOrigins) > 0 {
		origins = strings.Join(c.AllowedOrigins, ",")
	}
	return fmt.Sprintf("listen=%s redis=%s ping=%s pong=%s metrics=%t origins=%s",
		c.ListenAddr,
		c.RedisURL,
		c.PingInterval,
		c.PongTimeout,
		c.MetricsEnabled,
		origins,
	)
}
