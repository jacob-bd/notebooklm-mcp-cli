# NotebookLM MCP Server — hardened container image
# Based on UBI 10 with Chromium for CDP-based authentication
#
# Build:
#   podman build -t notebooklm-mcp -f Containerfile .
#
# Run (HTTP transport):
#   podman run -d --name mcp-notebooklm \
#     -p 8009:8000 \
#     --read-only \
#     --cap-drop=ALL \
#     --security-opt=no-new-privileges:true \
#     --pids-limit=100 \
#     --tmpfs /tmp:rw,noexec,nosuid,size=64m \
#     --secret notebooklm-cookies,target=/run/secrets/cookies \
#     -e NOTEBOOKLM_COOKIES_FILE=/run/secrets/cookies \
#     notebooklm-mcp

FROM registry.access.redhat.com/ubi10/ubi-minimal:latest AS base

# Install Python (Chromium not needed — auth injected via podman secrets)
RUN microdnf install -y \
    python3.12 \
    python3.12-pip \
    && microdnf clean all \
    && rm -rf /var/cache/yum

# Create non-root user
RUN groupadd -r mcp && useradd -r -g mcp -d /home/mcp -s /sbin/nologin mcp

# Set up app directory
WORKDIR /app

# Install package
COPY pyproject.toml ./
COPY src/ ./src/
RUN python3.12 -m pip install --no-cache-dir . \
    && python3.12 -m pip cache purge 2>/dev/null || true

# Home dir for non-root user (auth cache not needed — secrets injected at runtime)
RUN chown -R mcp:mcp /home/mcp

# Switch to non-root
USER mcp

# Health check
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python3.12 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

EXPOSE 8000

ENTRYPOINT ["notebooklm-mcp", "--transport", "http", "--port", "8000"]
