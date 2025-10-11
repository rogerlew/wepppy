package payload

// StatusMessage represents the JSON structure pushed to WebSocket clients.
type StatusMessage struct {
	Type string `json:"type"`
	Data string `json:"data"`
}

// PingMessage is the JSON payload for heartbeat pings.
var PingMessage = []byte(`{"type":"ping"}`)

// HangupMessage is the JSON payload sent when the server is shutting down the socket.
var HangupMessage = []byte(`{"type":"hangup"}`)
