# Bot Blocklist for WeppCloud

## Overview

This document lists known bots and crawlers that have caused performance issues on WeppCloud infrastructure. These bots generate high volumes of requests that can overwhelm the application, causing 502 errors and slow response times for legitimate users.

## Incident: 2026-02-03

Analysis of Caddy logs revealed aggressive crawling from the following bots causing 502 errors with response times of 25-62 seconds.

## Identified Problematic Bots

### High Priority (Aggressive Crawlers)

| Bot Name | User-Agent Pattern | Impact |
|----------|-------------------|--------|
| Meta/Facebook Crawler | `meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)` | High volume requests to `/browse/`, `/download/` endpoints |
| Bytespider (TikTok) | `Bytespider; spider-feedback@bytedance.com` | Aggressive crawling of run data files |

### Medium Priority (Monitor)

| Bot Name | User-Agent Pattern | Notes |
|----------|-------------------|-------|
| Googlebot | `Googlebot` | Generally well-behaved, but monitor |
| Bingbot | `bingbot` | Generally well-behaved |
| GPTBot | `GPTBot` | OpenAI crawler |
| ClaudeBot | `ClaudeBot` | Anthropic crawler |
| CCBot | `CCBot` | Common Crawl |

## Caddy Configuration

Add the following to the Caddyfile to block aggressive bots:

```caddy
# Bot blocking - add near the top of the server block
@blocked_bots {
    header User-Agent *meta-externalagent*
    header User-Agent *Bytespider*
}
respond @blocked_bots 403

# Rate limiting for other bots (requires rate_limit plugin)
@known_bots {
    header User-Agent *bot*
    header User-Agent *crawler*
    header User-Agent *spider*
}
```

## robots.txt Recommendations

Create or update `/srv/weppcloud/static/robots.txt`:

```
User-agent: meta-externalagent
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: GPTBot
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: ClaudeBot
Disallow: /weppcloud/runs/

# Allow legitimate search engines with crawl delay
User-agent: Googlebot
Crawl-delay: 10
Disallow: /weppcloud/runs/*/browse/
Disallow: /weppcloud/runs/*/download/

User-agent: Bingbot
Crawl-delay: 10
Disallow: /weppcloud/runs/*/browse/
Disallow: /weppcloud/runs/*/download/

User-agent: *
Crawl-delay: 5
Disallow: /weppcloud/runs/*/browse/
Disallow: /weppcloud/runs/*/download/
Disallow: /weppcloud/runs/*/dtale/
Disallow: /browse/
Disallow: /dtale/
```

## IP Ranges to Monitor

Based on incident logs, these IP ranges were associated with aggressive crawling:

| Range | Owner | Action |
|-------|-------|--------|
| `57.141.16.0/24` | Meta/Facebook | Block or rate limit |
| `47.128.0.0/16` | Bytespider/ByteDance | Block or rate limit |

## Implementation Steps

1. **Immediate**: Add bot blocking rules to Caddyfile
2. **Short-term**: Deploy updated robots.txt
3. **Long-term**: Consider implementing rate limiting per IP/User-Agent

## Monitoring

Check for bot traffic with:

```bash
# Recent bot 502 errors
docker logs docker-caddy-1 --tail=1000 2>&1 | grep -E "meta-externalagent|Bytespider" | wc -l

# All 502 errors in last hour
docker logs docker-caddy-1 --since 1h 2>&1 | grep '"status":502' | wc -l
```

## References

- [Meta Crawler Documentation](https://developers.facebook.com/docs/sharing/webmasters/crawler)
- [Caddy Rate Limiting](https://caddyserver.com/docs/caddyfile/directives/rate_limit)
- [robots.txt Specification](https://www.robotstxt.org/robotstxt.html)

