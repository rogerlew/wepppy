package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/redis/go-redis/v9"
	"golang.org/x/sync/errgroup"
	"nhooyr.io/websocket"

	"github.com/weppcloud/wepppy/services/preflight2/internal/checklist"
	"github.com/weppcloud/wepppy/services/preflight2/internal/config"
)

var (
	runIDPattern = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)
	pingPayload  = []byte(`{"type":"ping"}`)
	hangupPayload = []byte(`{"type":"hangup"}`)
)

// Server wires together configuration, Redis access, and HTTP handling.
type Server struct {
	cfg     config.Config
	logger  *slog.Logger
	redis   *redis.Client
	metrics *metrics
	redisDB int
}

// New constructs a Server from configuration.
func New(cfg config.Config, logger *slog.Logger) (*Server, error) {
	if logger == nil {
		logger = slog.Default()
	}
	logger = logger.With("component", "preflight2")

	opts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}
	if opts == nil {
		return nil, errors.New("redis options resolved to nil")
	}
	if opts.DB < 0 {
		opts.DB = 0
	}
	opts.ContextTimeoutEnabled = true
	client := redis.NewClient(opts)
	if err := client.Ping(context.Background()).Err(); err != nil {
		return nil, fmt.Errorf("redis ping: %w", err)
	}

	return &Server{
		cfg:     cfg,
		logger:  logger,
		redis:   client,
		metrics: newMetrics(cfg.MetricsEnabled),
		redisDB: opts.DB,
	}, nil
}

// Close releases redis resources.
func (s *Server) Close() error {
	if s.redis == nil {
		return nil
	}
	return s.redis.Close()
}

// Handler returns the HTTP handler serving health, metrics, and WebSockets.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", s.handleHealth)
	mux.Handle("/metrics", s.metrics.handler())
	mux.HandleFunc("/", s.handleWebsocket)
	return mux
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("OK"))
}

func (s *Server) handleWebsocket(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	path := strings.TrimPrefix(r.URL.Path, "/")
	if path == "" || path == "health" || path == "metrics" {
		http.NotFound(w, r)
		return
	}
	runID := strings.TrimSuffix(path, "/")
	if !runIDPattern.MatchString(runID) {
		http.Error(w, "invalid run id", http.StatusBadRequest)
		return
	}

	accept := &websocket.AcceptOptions{
		OriginPatterns: s.cfg.AllowedOrigins,
	}
	if len(s.cfg.AllowedOrigins) == 0 {
		accept.InsecureSkipVerify = true
	}

	conn, err := websocket.Accept(w, r, accept)
	if err != nil {
		s.logger.Warn("websocket accept failed", "run_id", runID, "error", err)
		return
	}
	defer func() {
		_ = conn.Close(websocket.StatusNormalClosure, "closing")
	}()
	conn.SetReadLimit(s.cfg.MaxMessageSize)

	ctx := r.Context()
	connLogger := s.logger.With("run_id", runID)
	connection := newConnection(s, connLogger, runID, conn)
	if err := connection.run(ctx); err != nil {
		if errors.Is(err, context.Canceled) {
			return
		}
		status := websocket.CloseStatus(err)
		if status == websocket.StatusNormalClosure || status == websocket.StatusGoingAway {
			return
		}
		connLogger.Warn("connection ended with error", "error", err)
	}
}

func (s *Server) keyspaceChannel(runID string) string {
	return fmt.Sprintf("__keyspace@%d__:%s", s.redisDB, runID)
}

type connection struct {
	srv      *Server
	logger   *slog.Logger
	runID    string
	ws       *websocket.Conn
	lastSeen atomic.Int64
	last     *checklist.Payload
	writeMu  sync.Mutex
}

func newConnection(srv *Server, logger *slog.Logger, runID string, ws *websocket.Conn) *connection {
	c := &connection{
		srv:    srv,
		logger: logger,
		runID:  runID,
		ws:     ws,
	}
	c.touch()
	return c
}

func (c *connection) run(ctx context.Context) error {
	c.srv.metrics.incConnections()
	defer c.srv.metrics.decConnections()

	defer c.sendHangup()

	if err := c.pushUpdate(ctx); err != nil {
		return err
	}

	group, ctx := errgroup.WithContext(ctx)
	group.Go(func() error {
		err := c.readLoop(ctx)
		if err != nil && !errors.Is(err, context.Canceled) {
			c.logger.Debug("read loop exited", "error", err)
		}
		return err
	})
	group.Go(func() error {
		err := c.pingLoop(ctx)
		if err != nil && !errors.Is(err, context.Canceled) {
			c.logger.Debug("ping loop exited", "error", err)
		}
		return err
	})
	group.Go(func() error {
		err := c.redisLoop(ctx)
		if err != nil && !errors.Is(err, context.Canceled) {
			c.logger.Debug("redis loop exited", "error", err)
		}
		return err
	})

	return group.Wait()
}

func (c *connection) readLoop(ctx context.Context) error {
	for {
		typ, data, err := c.ws.Read(ctx)
		if err != nil {
			return err
		}
		if typ != websocket.MessageText {
			continue
		}
		var msg struct {
			Type string `json:"type"`
		}
		if err := json.Unmarshal(data, &msg); err != nil {
			c.logger.Warn("invalid client message", "error", err)
			continue
		}
		switch strings.ToLower(msg.Type) {
		case "pong", "init":
			c.touch()
		default:
			// ignore other message types for forward compatibility
		}
	}
}

func (c *connection) pingLoop(ctx context.Context) error {
	ticker := time.NewTicker(c.srv.cfg.PingInterval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := c.writeRaw(ctx, pingPayload); err != nil {
				return err
			}
			if time.Since(time.Unix(0, c.lastSeen.Load())) > c.srv.cfg.PongTimeout {
				return errors.New("pong timeout exceeded")
			}
		}
	}
}

func (c *connection) redisLoop(ctx context.Context) error {
	attempt := 0
	channel := c.srv.keyspaceChannel(c.runID)
	base := c.srv.cfg.RedisRetryBase
	if base <= 0 {
		base = time.Second
	}

outer:
	for {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		pubsub := c.srv.redis.PSubscribe(ctx, channel)
		c.srv.metrics.incrRedisReconnects()
		if _, err := pubsub.Receive(ctx); err != nil {
			pubsub.Close()
			attempt++
			wait := c.redisBackoff(attempt, base)
			c.logger.Warn("redis subscription failed", "attempt", attempt, "error", err, "backoff", wait)
			if c.shouldAbort(attempt) {
				return fmt.Errorf("redis subscription failed after %d attempts: %w", attempt, err)
			}
			select {
			case <-time.After(wait):
				continue outer
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		attempt = 0
		for {
			msg, err := pubsub.ReceiveMessage(ctx)
			if err != nil {
				pubsub.Close()
				if ctx.Err() != nil {
					return ctx.Err()
				}
				attempt++
				wait := c.redisBackoff(attempt, base)
				c.logger.Warn("redis stream interrupted", "attempt", attempt, "error", err, "backoff", wait)
				if c.shouldAbort(attempt) {
					return fmt.Errorf("redis stream interrupted after %d attempts: %w", attempt, err)
				}
				select {
				case <-time.After(wait):
					continue outer
				case <-ctx.Done():
					return ctx.Err()
				}
			}
			attempt = 0
			c.logger.Debug("redis notification", "channel", msg.Channel, "payload", msg.Payload)
			if err := c.pushUpdate(ctx); err != nil {
				if errors.Is(err, context.Canceled) {
					pubsub.Close()
					return err
				}
				c.logger.Warn("failed to broadcast update", "error", err)
			}
		}
	}
}

func (c *connection) redisBackoff(attempt int, base time.Duration) time.Duration {
	if attempt <= 0 {
		return base
	}
	d := base * time.Duration(1<<uint(min(attempt-1, 10)))
	if d > c.srv.cfg.RedisRetryMax {
		return c.srv.cfg.RedisRetryMax
	}
	return d
}

func (c *connection) shouldAbort(attempt int) bool {
	if c.srv.cfg.RedisMaxRetries <= 0 {
		return false
	}
	return attempt >= c.srv.cfg.RedisMaxRetries
}

func (c *connection) pushUpdate(ctx context.Context) error {
	fetchCtx, cancel := context.WithTimeout(ctx, c.srv.cfg.RedisRequestTimeout)
	defer cancel()

	prep, err := c.srv.redis.HGetAll(fetchCtx, c.runID).Result()
	if err != nil {
		return err
	}

	check, locks := checklist.Evaluate(prep)
	payload := checklist.Payload{
		Type:         "preflight",
		Checklist:    check,
		LockStatuses: locks,
	}

	if c.last != nil && checklist.Equal(*c.last, payload) {
		c.logger.Info("preflight unchanged", "run_id", c.runID)
		return nil
	}
	if err := c.sendPayload(ctx, payload); err != nil {
		return err
	}
	c.logger.Info("preflight update", "run_id", c.runID, "checklist", payload.Checklist, "locks", payload.LockStatuses)
	copyPayload := payload
	c.last = &copyPayload
	return nil
}

func (c *connection) sendPayload(ctx context.Context, payload checklist.Payload) error {
	bytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	if err := c.writeRaw(ctx, bytes); err != nil {
		return err
	}
	c.srv.metrics.incrMessages()
	return nil
}

func (c *connection) writeRaw(ctx context.Context, data []byte) error {
	writeCtx, cancel := context.WithTimeout(ctx, c.srv.cfg.WriteTimeout)
	defer cancel()
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if err := c.ws.Write(writeCtx, websocket.MessageText, data); err != nil {
		c.srv.metrics.incrWriteErrors()
		return err
	}
	return nil
}

func (c *connection) sendHangup() {
	ctx, cancel := context.WithTimeout(context.Background(), c.srv.cfg.WriteTimeout)
	defer cancel()
	_ = c.writeRaw(ctx, hangupPayload)
}

func (c *connection) touch() {
	c.lastSeen.Store(time.Now().UnixNano())
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
