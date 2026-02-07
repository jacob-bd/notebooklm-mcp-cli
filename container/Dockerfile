# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Cache module downloads
COPY go.mod go.sum* ./
RUN go mod download 2>/dev/null || true

# Build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /notebooklm-mcp ./cmd/server

# Runtime stage — minimal image
FROM scratch

# CA certificates for HTTPS to notebooklm.google.com
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

COPY --from=builder /notebooklm-mcp /notebooklm-mcp

# Default to HTTP transport in container (stdio impractical for containers)
ENV NOTEBOOKLM_MCP_TRANSPORT=http
ENV NOTEBOOKLM_MCP_HOST=0.0.0.0
ENV NOTEBOOKLM_MCP_PORT=8000

EXPOSE 8000

ENTRYPOINT ["/notebooklm-mcp"]
