package server

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type metrics struct {
	registry         *prometheus.Registry
	connectionsGauge prometheus.Gauge
	messageCounter   prometheus.Counter
	redisReconnects  prometheus.Counter
	writeErrors      prometheus.Counter
}

func newMetrics(enabled bool) *metrics {
	if !enabled {
		return nil
	}
	reg := prometheus.NewRegistry()
	m := &metrics{
		registry: reg,
		connectionsGauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: "preflight2",
			Name:      "connections_active",
			Help:      "Number of active WebSocket connections.",
		}),
		messageCounter: prometheus.NewCounter(prometheus.CounterOpts{
			Namespace: "preflight2",
			Name:      "messages_sent_total",
			Help:      "Total number of preflight payloads sent to clients.",
		}),
		redisReconnects: prometheus.NewCounter(prometheus.CounterOpts{
			Namespace: "preflight2",
			Name:      "redis_reconnects_total",
			Help:      "Number of times the Redis subscription was recreated.",
		}),
		writeErrors: prometheus.NewCounter(prometheus.CounterOpts{
			Namespace: "preflight2",
			Name:      "write_errors_total",
			Help:      "Number of WebSocket write attempts that resulted in error.",
		}),
	}

	reg.MustRegister(m.connectionsGauge, m.messageCounter, m.redisReconnects, m.writeErrors)
	return m
}

func (m *metrics) handler() http.Handler {
	if m == nil {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			http.NotFound(w, r)
		})
	}
	return promhttp.HandlerFor(m.registry, promhttp.HandlerOpts{})
}

func (m *metrics) incConnections() {
	if m != nil {
		m.connectionsGauge.Inc()
	}
}

func (m *metrics) decConnections() {
	if m != nil {
		m.connectionsGauge.Dec()
	}
}

func (m *metrics) incrMessages() {
	if m != nil {
		m.messageCounter.Inc()
	}
}

func (m *metrics) incrRedisReconnects() {
	if m != nil {
		m.redisReconnects.Inc()
	}
}

func (m *metrics) incrWriteErrors() {
	if m != nil {
		m.writeErrors.Inc()
	}
}
