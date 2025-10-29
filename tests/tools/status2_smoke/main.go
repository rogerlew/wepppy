package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"math"
	"math/rand"
	"net/url"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"nhooyr.io/websocket"
	"nhooyr.io/websocket/wsjson"
)

const defaultWSURL = "ws://127.0.0.1:9002"
const defaultRedisURL = "redis://127.0.0.1:6379/2"

// StatusFrame represents the JSON payload emitted by status2.
type StatusFrame struct {
	Type string      `json:"type"`
	Data interface{} `json:"data,omitempty"`
}

func main() {
	var (
		wsURLFlag    = flag.String("ws", getenvOr("STATUS2_WS_URL", defaultWSURL), "WebSocket base URL for status2 (e.g. ws://127.0.0.1:9002)")
		redisURLFlag = flag.String("redis", getenvOr("STATUS2_REDIS_URL", defaultRedisURL), "Redis URL for publishing test messages")
		runIDFlag    = flag.String("run", "status2-smoke", "Run identifier for the channel")
		channelFlag  = flag.String("channel", "status2-smoke", "Channel name to exercise")
		timeoutFlag  = flag.Duration("timeout", 10*time.Second, "Overall timeout for the smoke test")
		samplesFlag  = flag.Int("samples", 1, "Number of messages to publish and measure")
		payloadSize  = flag.Int("payload-bytes", 0, "Extra payload size (bytes) appended to each message")
		quietFlag    = flag.Bool("quiet", false, "Reduce log chatter; exit code still reflects success")
	)
	flag.Parse()

	logger := log.New(os.Stdout, "status2-smoke: ", log.LstdFlags|log.Lmsgprefix)

	if *quietFlag {
		logger.SetOutput(os.Stdout)
		logger.SetFlags(0)
		logger.SetPrefix("")
	}

	ctx, cancel := context.WithTimeout(context.Background(), *timeoutFlag)
	defer cancel()

	wsURL, err := buildWebSocketURL(*wsURLFlag, *runIDFlag, *channelFlag)
	if err != nil {
		logger.Fatalf("invalid WebSocket URL: %v", err)
	}

	redisOpts, err := redis.ParseURL(*redisURLFlag)
	if err != nil {
		logger.Fatalf("invalid Redis URL: %v", err)
	}

	redisClient := redis.NewClient(redisOpts)
	defer func() {
		_ = redisClient.Close()
	}()

	logger.Printf("connecting to %s", wsURL)
	conn, resp, err := websocket.Dial(ctx, wsURL, nil)
	if err != nil {
		if resp != nil {
			logger.Fatalf("websocket dial failed: %v (HTTP %d)", err, resp.StatusCode)
		}
		logger.Fatalf("websocket dial failed: %v", err)
	}
	defer func() {
		_ = conn.Close(websocket.StatusNormalClosure, "smoke test complete")
	}()

	if *samplesFlag < 1 {
		logger.Fatalf("samples must be >= 1 (got %d)", *samplesFlag)
	}

	rand.Seed(time.Now().UnixNano())
	extraPayload := strings.Repeat("x", max(0, *payloadSize))
	redisChannel := fmt.Sprintf("%s:%s", *runIDFlag, *channelFlag)
	latencies := make([]time.Duration, 0, *samplesFlag)
	payloadBytes := 0

	for i := 0; i < *samplesFlag; i++ {
		token := fmt.Sprintf("%d-%d", rand.Int63(), i)
		payload := fmt.Sprintf("status2 smoke %s %s", token, extraPayload)
		payloadBytes = len(payload)

		logger.Printf("publishing payload %d/%d to redis channel %q (payload bytes=%d)", i+1, *samplesFlag, redisChannel, len(payload))
		if err := redisClient.Publish(ctx, redisChannel, payload).Err(); err != nil {
			logger.Fatalf("failed to publish test payload: %v", err)
		}

		recvCtx, recvCancel := context.WithTimeout(ctx, 5*time.Second)
		duration, err := waitForStatus(recvCtx, conn, token)
		recvCancel()
		if err != nil {
			logger.Fatalf("failed waiting for status payload: %v", err)
		}

		latency := duration
		logger.Printf("received status frame %d/%d after %s", i+1, *samplesFlag, latency.Truncate(time.Microsecond))
		latencies = append(latencies, latency)
	}

	reportLatencyStats(logger, latencies, payloadBytes)
	logger.Printf("status2 smoke test succeeded")
}

func buildWebSocketURL(base, runID, channel string) (string, error) {
	if runID == "" || channel == "" {
		return "", fmt.Errorf("runID and channel must be non-empty")
	}
	parsed, err := url.Parse(base)
	if err != nil {
		return "", err
	}
	if parsed.Scheme != "ws" && parsed.Scheme != "wss" {
		return "", fmt.Errorf("unsupported scheme %q", parsed.Scheme)
	}

	if !strings.HasSuffix(parsed.Path, "/") {
		parsed.Path += "/"
	}
	parsed.Path += fmt.Sprintf("%s:%s", url.PathEscape(runID), url.PathEscape(channel))
	return parsed.String(), nil
}

func getenvOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func waitForStatus(ctx context.Context, conn *websocket.Conn, token string) (time.Duration, error) {
	start := time.Now()
	var frame StatusFrame
	for {
		frame = StatusFrame{}
		if err := wsjson.Read(ctx, conn, &frame); err != nil {
			return 0, fmt.Errorf("read frame: %w", err)
		}

		switch strings.ToLower(frame.Type) {
		case "status":
			text := fmt.Sprint(frame.Data)
			if !strings.Contains(text, token) {
				continue
			}
			return time.Since(start), nil
		case "ping":
			_ = wsjson.Write(context.Background(), conn, StatusFrame{Type: "pong"})
		default:
			continue
		}
	}
}

func reportLatencyStats(logger *log.Logger, latencies []time.Duration, payloadBytes int) {
	if len(latencies) == 0 {
		logger.Println("no latency samples recorded")
		return
	}

	samples := make([]float64, len(latencies))
	for i, d := range latencies {
		samples[i] = float64(d) / float64(time.Millisecond)
	}
	sort.Float64s(samples)

	total := 0.0
	min := samples[0]
	max := samples[len(samples)-1]
	for _, s := range samples {
		total += s
	}
	mean := total / float64(len(samples))
	median := samples[len(samples)/2]
	p95 := percentile(samples, 95)

	logger.Printf("latency summary (milliseconds) samples=%d payload-bytes=%d", len(samples), payloadBytes)
	logger.Printf("  min=%.3f  median=%.3f  mean=%.3f  p95=%.3f  max=%.3f", min, median, mean, p95, max)
}

func percentile(samples []float64, p float64) float64 {
	if len(samples) == 0 {
		return math.NaN()
	}
	if p <= 0 {
		return samples[0]
	}
	if p >= 100 {
		return samples[len(samples)-1]
	}
	rank := (p / 100.0) * float64(len(samples)-1)
	lower := int(math.Floor(rank))
	upper := int(math.Ceil(rank))
	weight := rank - float64(lower)
	if upper >= len(samples) {
		upper = len(samples) - 1
	}
	return samples[lower]*(1-weight) + samples[upper]*weight
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
