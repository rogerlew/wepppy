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
	"sync"
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
		samplesFlag  = flag.Int("samples", 1, "Number of messages to publish and measure per client")
		payloadSize  = flag.Int("payload-bytes", 0, "Extra payload size (bytes) appended to each message")
		clientsFlag  = flag.Int("clients", 1, "Number of concurrent WebSocket clients")
		recvTimeout  = flag.Duration("receive-timeout", 10*time.Second, "Per-message receive timeout")
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

	if *samplesFlag < 1 {
		logger.Fatalf("samples must be >= 1 (got %d)", *samplesFlag)
	}
	if *clientsFlag < 1 {
		logger.Fatalf("clients must be >= 1 (got %d)", *clientsFlag)
	}

	extraPayload := strings.Repeat("x", max(0, *payloadSize))
	redisChannel := fmt.Sprintf("%s:%s", *runIDFlag, *channelFlag)

	type result struct {
		latencies   []time.Duration
		payloadSize int
		err         error
	}

	results := make(chan result, *clientsFlag)
	var wg sync.WaitGroup

	for clientID := 0; clientID < *clientsFlag; clientID++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			latencies, payloadBytes, err := runClient(ctx, logger, id, *samplesFlag, extraPayload, redisClient, wsURL, redisChannel, *recvTimeout)
			results <- result{latencies: latencies, payloadSize: payloadBytes, err: err}
		}(clientID)
	}

	wg.Wait()
	close(results)

	var (
		allLatencies []time.Duration
		payloadBytes int
	)

	for res := range results {
		if res.err != nil {
			logger.Fatalf("client error: %v", res.err)
		}
		allLatencies = append(allLatencies, res.latencies...)
		if res.payloadSize > 0 {
			payloadBytes = res.payloadSize
		}
	}

	reportLatencyStats(logger, allLatencies, payloadBytes, *clientsFlag, *samplesFlag)
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

func runClient(
	ctx context.Context,
	logger *log.Logger,
	clientID int,
	samples int,
	extraPayload string,
	redisClient *redis.Client,
	wsURL string,
	redisChannel string,
	recvTimeout time.Duration,
) ([]time.Duration, int, error) {
	logger.Printf("[client %d] connecting to %s", clientID, wsURL)
	conn, resp, err := websocket.Dial(ctx, wsURL, nil)
	if err != nil {
		if resp != nil {
			return nil, 0, fmt.Errorf("client %d websocket dial failed: %w (HTTP %d)", clientID, err, resp.StatusCode)
		}
		return nil, 0, fmt.Errorf("client %d websocket dial failed: %w", clientID, err)
	}
	defer func() {
		_ = conn.Close(websocket.StatusNormalClosure, "client complete")
	}()

	latencies := make([]time.Duration, 0, samples)
	rng := rand.New(rand.NewSource(time.Now().UnixNano() + int64(clientID)*1_000_000))
	payloadBytes := 0

	for sampleIdx := 0; sampleIdx < samples; sampleIdx++ {
		token := fmt.Sprintf("c%d-%d-%d", clientID, sampleIdx, rng.Int63())
		payload := fmt.Sprintf("status2 smoke client=%d sample=%d %s %s", clientID, sampleIdx, token, extraPayload)
		payloadBytes = len(payload)

		logger.Printf("[client %d] publishing payload %d/%d to %q (payload bytes=%d)", clientID, sampleIdx+1, samples, redisChannel, payloadBytes)
		if err := redisClient.Publish(ctx, redisChannel, payload).Err(); err != nil {
			return nil, 0, fmt.Errorf("client %d publish failed: %w", clientID, err)
		}

		recvCtx, recvCancel := context.WithTimeout(ctx, recvTimeout)
		duration, err := waitForStatus(recvCtx, conn, token)
		recvCancel()
		if err != nil {
			return nil, 0, fmt.Errorf("client %d wait failed: %w", clientID, err)
		}

		logger.Printf("[client %d] received status frame %d/%d after %s", clientID, sampleIdx+1, samples, duration.Truncate(time.Microsecond))
		latencies = append(latencies, duration)
	}

	return latencies, payloadBytes, nil
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

func reportLatencyStats(logger *log.Logger, latencies []time.Duration, payloadBytes int, clients int, samplesPerClient int) {
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

	logger.Printf(
		"latency summary (milliseconds) clients=%d samples-per-client=%d total-samples=%d payload-bytes=%d",
		clients,
		samplesPerClient,
		len(samples),
		payloadBytes,
	)
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
