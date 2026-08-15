# syntax=docker/dockerfile:1
ARG NODE_BASE_IMAGE=node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293
FROM ${NODE_BASE_IMAGE}

WORKDIR /app

ARG CAP_REPO=https://github.com/tiagozip/cap
ARG CAP_REF=e069d5e8174527f997167d45a65eb724ed0a607d

RUN apk add --no-cache git ca-certificates && \
    git init /opt/cap && \
    git -C /opt/cap remote add origin "${CAP_REPO}" && \
    git -C /opt/cap fetch --depth=1 origin "${CAP_REF}" && \
    git -C /opt/cap checkout --detach FETCH_HEAD && \
    test "$(git -C /opt/cap rev-parse HEAD)" = "${CAP_REF}" && \
    rm -rf /opt/cap/.git

COPY services/cap/package.json services/cap/package-lock.json ./
RUN npm ci --omit=dev

COPY services/cap/server.js services/cap/config.js ./

RUN addgroup -g 10001 -S cap && \
    adduser -u 10001 -S -D -H -G cap cap && \
    mkdir -p /var/lib/cap && \
    chown -R cap:cap /app /var/lib/cap

ENV NODE_ENV=production

EXPOSE 3000

USER 10001:10001
CMD ["node", "server.js"]
