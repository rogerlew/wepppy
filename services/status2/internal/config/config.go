package config

import (
	"fmt"
	"log/slog"
	"net"

	"os"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/redis/go-redis/v9"
	"github.com/rogerlew/wepppy/services/streamauth"
)

type Config struct {
	ListenAddr          string
	RedisEndpoint       string
	RedisOptions        *redis.Options
	SigningKeyFile      string
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
	defaultRedisEndpoint      = "redis://localhost:6379/2"
	defaultRedisHost          = "localhost"
	defaultRedisPort          = "6379"
	defaultRedisDB            = "2"
	defaultPingInterval       = 5 * time.Second
	defaultPongTimeout        = 75 * time.Second
	defaultWriteTimeout       = 2 * time.Second
	defaultRedisRequestTimout = time.Second
	defaultRedisRetryBase     = time.Second
	defaultRedisRetryMax      = 30 * time.Second
	defaultRedisMaxRetries    = 5
	defaultLogLevel           = slog.LevelInfo
	defaultMaxMessageSize     = 64 * 1024
)

func Load() (Config, error) {
	redisURL, opts, err := resolveRedisEndpoint()
	if err != nil {
		return Config{}, err
	}

	cfg := Config{
		ListenAddr:          getEnv("LISTEN_ADDR", defaultListenAddr),
		RedisEndpoint:       redisURL,
		RedisOptions:        opts,
		SigningKeyFile:      os.Getenv("WEPP_AUTH_JWT_SECRETS_FILE"),
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

func resolveRedisEndpoint() (string, *redis.Options, error) {
	password, err := resolveRedisPassword()
	if err != nil {
		return "", nil, err
	}
	raw := os.Getenv(envKey("REDIS_URL"))
	if raw == "" {
		raw = os.Getenv("REDIS_URL")
	}
	if raw == "" {
		host := os.Getenv("REDIS_HOST")
		if host == "" {
			host = defaultRedisHost
		}
		if strings.ContainsAny(host, "/?#@\\") || strings.IndexFunc(host, unicode.IsSpace) >= 0 {
			return "", nil, fmt.Errorf("invalid Redis host")
		}
		port := os.Getenv("REDIS_PORT")
		if port == "" {
			port = defaultRedisPort
		}
		raw = "redis://" + net.JoinHostPort(host, port) + "/" + defaultRedisDB
	}
	return streamauth.ParseRedisEndpoint(raw, password)
}

func resolveRedisPassword() (string, error) {
	if path := strings.TrimSpace(os.Getenv(envKey("REDIS_PASSWORD_FILE"))); path != "" {
		return readSecretFile(path, envKey("REDIS_PASSWORD_FILE"))
	}
	if path := strings.TrimSpace(os.Getenv("REDIS_PASSWORD_FILE")); path != "" {
		return readSecretFile(path, "REDIS_PASSWORD_FILE")
	}

	if v := strings.TrimSpace(os.Getenv(envKey("REDIS_PASSWORD"))); v != "" {
		return v, nil
	}
	if v := strings.TrimSpace(os.Getenv("REDIS_PASSWORD")); v != "" {
		return v, nil
	}
	return "", nil
}

func readSecretFile(path string, label string) (string, error) {
	contents, err := os.ReadFile(path)
	if err != nil {
		return "", fmt.Errorf("unable to read %s at %s: %w", label, path, err)
	}
	value := strings.TrimRight(string(contents), "\n")
	if !utf8.Valid(contents) || value != strings.TrimFunc(value, func(r rune) bool { return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f) }) || strings.ContainsAny(value, "\x00\r\n") {
		return "", fmt.Errorf("invalid Redis password file framing")
	}
	if value == "" {
		return "", fmt.Errorf("%s at %s is empty", label, path)
	}
	return value, nil
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
		c.RedisEndpoint,
		c.PingInterval,
		c.PongTimeout,
		c.MetricsEnabled,
		origins,
	)
}
