package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math/rand"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/redis/go-redis/v9"
	"golang.org/x/sync/errgroup"
	"nhooyr.io/websocket"

	"github.com/weppcloud/wepppy/services/status2/internal/config"
	"github.com/weppcloud/wepppy/services/status2/internal/payload"
)

var channelPattern = regexp.MustCompile(`^[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$`)

// Server provides HTTP/WebSocket handling backed by Redis Pub/Sub.
type Server struct {
	cfg    config.Config
	logger *slog.Logger
	redis  *redis.Client
	metric *metrics
}

// New constructs a Server from configuration.
func New(cfg config.Config, logger *slog.Logger) (*Server, error) {
	if logger == nil {
		logger = slog.Default()
	}
	logger = logger.With("component", "status2")

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
		cfg:    cfg,
		logger: logger,
		redis:  client,
		metric: newMetrics(cfg.MetricsEnabled),
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
	mux.Handle("/metrics", s.metric.handler())
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
	path = strings.TrimSuffix(path, "/")
	if !channelPattern.MatchString(path) {
		http.Error(w, "invalid channel", http.StatusBadRequest)
		return
	}
	runID, channel, _ := strings.Cut(path, ":")

	accept := &websocket.AcceptOptions{OriginPatterns: s.cfg.AllowedOrigins}
	if len(s.cfg.AllowedOrigins) == 0 {
		accept.InsecureSkipVerify = true
	}

	conn, err := websocket.Accept(w, r, accept)
	if err != nil {
		s.logger.Warn("websocket accept failed", "run_id", runID, "channel", channel, "error", err)
		return
	}
	defer func() { _ = conn.Close(websocket.StatusNormalClosure, "closing") }()
	conn.SetReadLimit(s.cfg.MaxMessageSize)

	ctx := r.Context()
	connLogger := s.logger.With("run_id", runID, "channel", channel)
	connection := newConnection(s, connLogger, runID, channel, conn)
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

type connection struct {
	srv      *Server
	logger   *slog.Logger
	runID    string
	channel  string
	ws       *websocket.Conn
	lastSeen atomic.Int64
	writeMu  sync.Mutex
	rand     *rand.Rand
}

func newConnection(srv *Server, logger *slog.Logger, runID, channel string, ws *websocket.Conn) *connection {
	c := &connection{
		srv:     srv,
		logger:  logger,
		runID:   runID,
		channel: channel,
		ws:      ws,
		rand:    rand.New(rand.NewSource(time.Now().UnixNano())),
	}
	c.touch()
	return c
}

func (c *connection) run(ctx context.Context) error {
	c.srv.metric.incConnections()
	defer c.srv.metric.decConnections()
	defer c.sendHangup()

	group, ctx := errgroup.WithContext(ctx)
	group.Go(func() error { return c.readLoop(ctx) })
	group.Go(func() error { return c.pingLoop(ctx) })
	group.Go(func() error { return c.redisLoop(ctx) })

	return group.Wait()
}

func (c *connection) readLoop(ctx context.Context) error {
	for {
		messageType, data, err := c.ws.Read(ctx)
		if err != nil {
			return err
		}
		if messageType != websocket.MessageText {
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
			// ignore unknown messages for forward compatibility
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
			if err := c.writeRaw(ctx, payload.PingMessage); err != nil {
				return err
			}
			c.logger.Debug("sent ping to client")
			if time.Since(time.Unix(0, c.lastSeen.Load())) > c.srv.cfg.PongTimeout {
				return errors.New("pong timeout exceeded")
			}
		}
	}
}

func (c *connection) redisLoop(ctx context.Context) error {
	attempt := 0
	channel := fmt.Sprintf("%s:%s", c.runID, c.channel)
	base := c.srv.cfg.RedisRetryBase
	if base <= 0 {
		base = time.Second
	}

outer:
	for {
		if ctx.Err() != nil {
			return ctx.Err()
		}

		pubsub := c.srv.redis.Subscribe(ctx, channel)
		c.srv.metric.incrRedisReconnects()

		var closeOnce sync.Once
		closePubsub := func(reason string) {
			closeOnce.Do(func() {
				if err := pubsub.Close(); err != nil {
					c.logger.Debug("pubsub close error", "reason", reason, "error", err)
				}
			})
		}

		cancelCh := make(chan struct{})
		var cancelOnce sync.Once
		cancelWatcher := func() {
			cancelOnce.Do(func() {
				close(cancelCh)
			})
		}

		go func() {
			select {
			case <-ctx.Done():
				closePubsub("context canceled")
			case <-cancelCh:
			}
		}()

		receiveAckCtx, cancelAck := c.redisRequestContext(ctx)
		_, err := pubsub.Receive(receiveAckCtx)
		cancelAck()
		if err != nil {
			cancelWatcher()
			closePubsub("subscribe ack failed")
			attempt++
			wait := c.redisBackoff(attempt, base)
			c.logger.Warn("redis subscribe failed", "attempt", attempt, "error", err, "backoff", wait)
			if c.shouldAbort(attempt) {
				return fmt.Errorf("redis subscribe failed after %d attempts: %w", attempt, err)
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
			messageCtx, cancel := c.redisRequestContext(ctx)
			msg, err := pubsub.ReceiveMessage(messageCtx)
			cancel()
			if err != nil {
				cancelWatcher()
				closePubsub("receive message failed")
				if ctx.Err() != nil {
					return ctx.Err()
				}
				attempt++
				wait := c.redisBackoff(attempt, base)
				c.logger.Warn("redis stream interrupted", "attempt", attempt, "error", err, "backoff", wait)
				if c.shouldAbort(attempt) {
					closePubsub("stream aborted")
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
			if err := c.forward(ctx, msg.Payload); err != nil {
				if errors.Is(err, context.Canceled) {
					cancelWatcher()
					closePubsub("forward canceled")
					return err
				}
				c.logger.Warn("failed to forward message", "error", err)
			}
		}
	}
}

func (c *connection) forward(ctx context.Context, data string) error {
	out := payload.StatusMessage{
		Type: "status",
		Data: data,
	}
	bytes, err := json.Marshal(out)
	if err != nil {
		return err
	}
	c.srv.metric.incrMessages()
	return c.writeRaw(ctx, bytes)
}

func (c *connection) writeRaw(ctx context.Context, data []byte) error {
	writeCtx, cancel := context.WithTimeout(ctx, c.srv.cfg.WriteTimeout)
	defer cancel()
	c.writeMu.Lock()
	defer c.writeMu.Unlock()
	if err := c.ws.Write(writeCtx, websocket.MessageText, data); err != nil {
		c.srv.metric.incrWriteErrors()
		return err
	}
	return nil
}

func (c *connection) sendHangup() {
	ctx, cancel := context.WithTimeout(context.Background(), c.srv.cfg.WriteTimeout)
	defer cancel()
	c.logger.Debug("sending hangup to client")
	_ = c.writeRaw(ctx, payload.HangupMessage)
}

func (c *connection) touch() {
	c.lastSeen.Store(time.Now().UnixNano())
}

func (c *connection) redisBackoff(attempt int, base time.Duration) time.Duration {
	if attempt <= 0 {
		return base
	}
	maxBackoff := base * time.Duration(1<<uint(min(attempt-1, 10)))
	if maxBackoff > c.srv.cfg.RedisRetryMax {
		maxBackoff = c.srv.cfg.RedisRetryMax
	}
	if maxBackoff <= base {
		return maxBackoff
	}

	jitterRange := maxBackoff - base
	if jitterRange <= 0 {
		return maxBackoff
	}
	return base + time.Duration(c.rand.Int63n(int64(jitterRange)+1))
}

func (c *connection) shouldAbort(attempt int) bool {
	if c.srv.cfg.RedisMaxRetries <= 0 {
		return false
	}
	return attempt >= c.srv.cfg.RedisMaxRetries
}

func (c *connection) redisRequestContext(parent context.Context) (context.Context, context.CancelFunc) {
	timeout := c.srv.cfg.RedisRequestTimeout
	if timeout <= 0 {
		return parent, func() {}
	}
	return context.WithTimeout(parent, timeout)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
