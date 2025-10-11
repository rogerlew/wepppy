# syntax=docker/dockerfile:1

FROM golang:1.25-alpine AS build
WORKDIR /src

COPY services/status2/go.mod ./
RUN go mod download

COPY services/status2/ ./
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /status2 ./cmd/status2

FROM gcr.io/distroless/static:nonroot
COPY --from=build /status2 /status2
EXPOSE 9002
ENTRYPOINT ["/status2"]
