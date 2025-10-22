package main

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/redis/go-redis/v9"

	"github.com/rogerlew/wepppy/services/preflight2/internal/config"
	"github.com/rogerlew/wepppy/services/preflight2/internal/server"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		slog.New(slog.NewJSONHandler(os.Stderr, nil)).Error("configuration error", "error", err)
		os.Exit(1)
	}

	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: cfg.LogLevel}))
	logger.Info("starting preflight2", "config", cfg.String())

	if _, err := redis.ParseURL(cfg.RedisURL); err != nil {
		logger.Error("invalid redis url", "error", err)
		os.Exit(1)
	}

	srv, err := initServerWithRetry(cfg, logger)
	if err != nil {
		logger.Error("failed to construct server", "error", err)
		os.Exit(1)
	}
	defer srv.Close()

	httpServer := &http.Server{
		Addr:              cfg.ListenAddr,
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       cfg.PongTimeout + cfg.PingInterval,
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	serverErr := make(chan error, 1)
	go func() {
		serverErr <- httpServer.ListenAndServe()
	}()

	select {
	case err := <-serverErr:
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("http server exited unexpectedly", "error", err)
			os.Exit(1)
		}
	case <-ctx.Done():
		logger.Info("shutdown signal received")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		if err := httpServer.Shutdown(shutdownCtx); err != nil {
			logger.Error("graceful shutdown failed", "error", err)
			os.Exit(1)
		}
	}

	logger.Info("preflight2 stopped")
}

func initServerWithRetry(cfg config.Config, logger *slog.Logger) (*server.Server, error) {
	backoff := cfg.RedisRetryBase
	if backoff <= 0 {
		backoff = time.Second
	}
	maxBackoff := cfg.RedisRetryMax
	if maxBackoff <= 0 {
		maxBackoff = 30 * time.Second
	}

	for attempt := 0; ; attempt++ {
		srv, err := server.New(cfg, logger)
		if err == nil {
			if attempt > 0 {
				logger.Info("connected to redis after retry", "attempts", attempt+1)
			}
			return srv, nil
		}

		if !retryableInitError(err) {
			return nil, err
		}

		if cfg.RedisMaxRetries > 0 && attempt+1 >= cfg.RedisMaxRetries {
			return nil, err
		}

		sleep := backoff
		if sleep > maxBackoff {
			sleep = maxBackoff
		}
		logger.Warn("redis unavailable, retrying", "error", err, "attempt", attempt+1, "backoff", sleep)
		time.Sleep(sleep)

		if backoff < maxBackoff {
			backoff *= 2
			if backoff > maxBackoff {
				backoff = maxBackoff
			}
		}
	}
}

func retryableInitError(err error) bool {
	if err == nil {
		return false
	}

	var netErr net.Error
	if errors.As(err, &netErr) {
		return true
	}

	var dnsErr *net.DNSError
	if errors.As(err, &dnsErr) {
		return true
	}

	if errors.Is(err, io.EOF) {
		return true
	}

	return false
}
