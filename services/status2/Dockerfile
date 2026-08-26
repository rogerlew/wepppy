# syntax=docker/dockerfile:1

ARG GO_BUILDER_IMAGE=golang:1.25-alpine@sha256:3eb6c2b3db8d55e38537302edb510b4417f8a115efbd5906d131ceba9468e29a
ARG RUNTIME_IMAGE=gcr.io/distroless/static:nonroot@sha256:f7f8f729987ad0fdf6b05eeeae94b26e6a0f613bdf46feea7fc40f7bd72953e6

FROM ${GO_BUILDER_IMAGE} AS build
WORKDIR /src

COPY services/status2/go.mod ./
RUN go mod download

COPY services/status2/ ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /status2 ./cmd/status2

FROM ${RUNTIME_IMAGE}
COPY --from=build /status2 /status2
EXPOSE 9002
ENTRYPOINT ["/status2"]
