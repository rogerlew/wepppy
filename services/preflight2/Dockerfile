# syntax=docker/dockerfile:1

FROM golang:1.25-alpine AS build
WORKDIR /src

COPY services/preflight2/go.mod ./
RUN go mod download
COPY services/preflight2/ ./
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o /preflight2 ./cmd/preflight2

FROM gcr.io/distroless/static:nonroot
COPY --from=build /preflight2 /preflight2
EXPOSE 9001
ENTRYPOINT ["/preflight2"]
