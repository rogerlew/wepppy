// Package streamauth implements the shared, fail-closed browser stream boundary.
package streamauth

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/redis/go-redis/v9"
)

const Protocol = "wepp-stream.v1"
const ExpiredCode = 4001

var configPattern = regexp.MustCompile(`^[a-z0-9_-]+$`)
var idPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`)

type Validator struct {
	keys     [][]byte
	origins  map[string]bool
	sessions *redis.Client
	revoked  *redis.Client
}

type Grant struct{ Expires time.Time }

// New uses the existing Redis host/auth but canonical DBs 11 (sessions) and 0 (JTI).
// Signing keys are read only from the same comma-separated secret file as Python.
func New(secretFile string, redisOptions *redis.Options, origins []string) (*Validator, error) {
	if secretFile == "" || len(origins) == 0 {
		return nil, errors.New("stream authorization configuration required")
	}
	raw, err := os.ReadFile(secretFile)
	if err != nil {
		return nil, errors.New("stream signing file unavailable")
	}
	v := &Validator{origins: make(map[string]bool)}
	for _, key := range strings.Split(strings.TrimSpace(string(raw)), ",") {
		key = strings.TrimSpace(key)
		if key == "" {
			return nil, errors.New("empty stream signing key")
		}
		v.keys = append(v.keys, []byte(key))
	}
	for _, origin := range origins {
		normalized := normalizeOrigin(origin)
		if normalized == "" {
			return nil, errors.New("invalid allowed stream origin")
		}
		v.origins[normalized] = true
	}
	if redisOptions == nil {
		return nil, errors.New("authorization Redis configuration required")
	}
	copyOptions := *redisOptions
	opts := &copyOptions
	opts.DB = 11
	opts.ContextTimeoutEnabled = true
	opts.DialTimeout = time.Second
	opts.ReadTimeout = time.Second
	opts.WriteTimeout = time.Second
	opts.MaxRetries = 0
	v.sessions = redis.NewClient(opts)
	copyOpts := *opts
	copyOpts.DB = 0
	v.revoked = redis.NewClient(&copyOpts)
	return v, nil
}

func (v *Validator) Close() error { return errors.Join(v.sessions.Close(), v.revoked.Close()) }

func normalizeOrigin(raw string) string {
	u, err := url.Parse(raw)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Hostname() == "" ||
		u.User != nil || u.Path != "" || u.RawQuery != "" || u.Fragment != "" || strings.ContainsAny(raw, "* ,\t\r\n") {
		return ""
	}
	port := u.Port()
	if port == "" {
		if u.Scheme == "https" {
			port = "443"
		} else {
			port = "80"
		}
	}
	n, err := strconv.Atoi(port)
	if err != nil || n < 1 || n > 65535 {
		return ""
	}
	return u.Scheme + "://" + strings.ToLower(u.Hostname()) + ":" + port
}

// uniqueObject rejects duplicate top-level fields, including conflicting claim/header keys.
func uniqueObject(segment string) bool {
	raw, err := base64.RawURLEncoding.DecodeString(segment)
	if err != nil {
		return false
	}
	d := json.NewDecoder(strings.NewReader(string(raw)))
	t, err := d.Token()
	if err != nil || t != json.Delim('{') {
		return false
	}
	seen := map[string]bool{}
	for d.More() {
		t, err = d.Token()
		key, ok := t.(string)
		if err != nil || !ok || seen[key] {
			return false
		}
		seen[key] = true
		var value json.RawMessage
		if d.Decode(&value) != nil {
			return false
		}
	}
	if _, err = d.Token(); err != nil {
		return false
	}
	_, err = d.Token()
	return err == io.EOF
}

func integer(c jwt.MapClaims, key string) (int64, bool) {
	n, ok := c[key].(json.Number)
	if !ok {
		return 0, false
	}
	i, err := n.Int64()
	return i, err == nil
}
func str(c jwt.MapClaims, key string) string { s, _ := c[key].(string); return s }

// Authorize returns only a fixed HTTP status on denial, never parser/Redis errors.
// No run-specific subscription/hash read may precede this call.
func (v *Validator) Authorize(r *http.Request, run, channel, service string) (Grant, int) {
	origins := r.Header.Values("Origin")
	if len(origins) != 1 || !v.origins[normalizeOrigin(origins[0])] {
		return Grant{}, http.StatusForbidden
	}
	q, err := url.ParseQuery(r.URL.RawQuery)
	if err != nil || len(q) != 1 || len(q["config"]) != 1 || !configPattern.MatchString(q.Get("config")) {
		return Grant{}, http.StatusBadRequest
	}
	raw := strings.Join(r.Header.Values("Sec-WebSocket-Protocol"), ",")
	if len(raw) > 8192 {
		return Grant{}, http.StatusBadRequest
	}
	protocols := strings.Split(raw, ",")
	if len(protocols) != 2 {
		return Grant{}, http.StatusUnauthorized
	}
	credential, fixed := "", false
	for _, p := range protocols {
		p = strings.TrimSpace(p)
		if p == Protocol && !fixed {
			fixed = true
		} else if strings.HasPrefix(p, "bearer.") && credential == "" {
			credential = strings.TrimPrefix(p, "bearer.")
		} else {
			return Grant{}, http.StatusUnauthorized
		}
	}
	parts := strings.Split(credential, ".")
	if !fixed || len(parts) != 3 || !uniqueObject(parts[0]) || !uniqueObject(parts[1]) {
		return Grant{}, http.StatusUnauthorized
	}
	var claims jwt.MapClaims
	valid := false
	for _, key := range v.keys {
		claims = jwt.MapClaims{}
		token, parseErr := jwt.ParseWithClaims(credential, claims, func(t *jwt.Token) (any, error) { return key, nil },
			jwt.WithValidMethods([]string{"HS256"}), jwt.WithIssuer("weppcloud-stream"),
			jwt.WithAudience("wepp-"+service), jwt.WithExpirationRequired(), jwt.WithIssuedAt(), jwt.WithJSONNumber())
		if parseErr == nil && token.Valid {
			valid = true
			break
		}
	}
	if !valid {
		return Grant{}, http.StatusUnauthorized
	}
	iat, iok := integer(claims, "iat")
	nbf, nok := integer(claims, "nbf")
	exp, eok := integer(claims, "exp")
	now := time.Now().Unix()
	if !iok || !nok || !eok || iat <= 0 || nbf != iat || exp <= iat || exp-iat > 300 || iat > now || exp <= now ||
		str(claims, "aud") != "wepp-"+service || str(claims, "token_class") != "session" ||
		str(claims, "stream") != service || str(claims, "scope") != service+":read" ||
		str(claims, "runid") != run || str(claims, "config") != q.Get("config") {
		return Grant{}, http.StatusUnauthorized
	}
	sid, jti := str(claims, "session_id"), str(claims, "jti")
	if !idPattern.MatchString(sid) || !idPattern.MatchString(jti) || str(claims, "sub") != sid {
		return Grant{}, http.StatusUnauthorized
	}
	_, operation := claims["operation"]
	_, job := claims["job_id"]
	_, scopedChannel := claims["channel"]
	if operation || job || scopedChannel {
		if service != "status" || channel != "run_sync" || str(claims, "operation") != "run-sync" ||
			str(claims, "channel") != channel || !idPattern.MatchString(str(claims, "job_id")) {
			return Grant{}, http.StatusForbidden
		}
	}
	ctx, cancel := context.WithTimeout(r.Context(), time.Second)
	defer cancel()
	pipe := v.sessions.Pipeline()
	marker := pipe.Exists(ctx, "auth:session:run:"+run+":"+sid)
	fence := pipe.Exists(ctx, "auth:session:revoked:"+sid)
	if _, err = pipe.Exec(ctx); err != nil {
		return Grant{}, http.StatusServiceUnavailable
	}
	revoked, err := v.revoked.Exists(ctx, "auth:jwt:revoked:"+jti).Result()
	if err != nil {
		return Grant{}, http.StatusServiceUnavailable
	}
	if marker.Val() != 1 || fence.Val() != 0 || revoked != 0 {
		return Grant{}, http.StatusUnauthorized
	}
	// Redis latency must not carry admission past expiry.
	if time.Now().Unix() >= exp {
		return Grant{}, http.StatusUnauthorized
	}
	return Grant{Expires: time.Unix(exp, 0)}, 0
}
