package streamauth

import (
	"errors"
	"net/url"
	"strconv"
	"strings"

	"github.com/redis/go-redis/v9"
)

// ParseRedisEndpoint separates legacy userinfo immediately. Options retain only
// a non-printing credentials closure; neither endpoint nor Options exposes it.
func ParseRedisEndpoint(raw, password string) (string, *redis.Options, error) {
	invalid := errors.New("invalid or conflicting Redis configuration")
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Fragment != "" {
		return "", nil, invalid
	}
	if parsed.Scheme != "unix" {
		if (parsed.Scheme != "redis" && parsed.Scheme != "rediss") || parsed.Hostname() == "" {
			return "", nil, invalid
		}
		if port := parsed.Port(); port != "" {
			n, err := strconv.Atoi(port)
			if err != nil || n < 1 || n > 65535 {
				return "", nil, invalid
			}
		}
	} else if parsed.Path == "" {
		return "", nil, invalid
	}
	username := ""
	if parsed.User != nil {
		username = parsed.User.Username()
		legacy, present := parsed.User.Password()
		if present {
			if legacy == "" {
				return "", nil, invalid
			}
			if password != "" && password != legacy {
				return "", nil, invalid
			}
			if password == "" {
				password = legacy
			}
		}
		parsed.User = nil
	}
	if strings.ContainsAny(password, "\x00\r\n") {
		return "", nil, invalid
	}
	query, err := url.ParseQuery(parsed.RawQuery)
	if err != nil {
		return "", nil, invalid
	}
	for _, key := range []string{"password", "username", "credential_provider"} {
		if _, ok := query[key]; ok {
			return "", nil, invalid
		}
	}
	endpoint := parsed.String()
	opts, err := redis.ParseURL(endpoint)
	if err != nil || opts.DB < 0 {
		return "", nil, invalid
	}
	if password != "" || username != "" {
		opts.CredentialsProvider = func() (string, string) { return username, password }
	}
	return endpoint, opts, nil
}
