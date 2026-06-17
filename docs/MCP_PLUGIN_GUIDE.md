# NotebookLM MCP Plugin Guide

NotebookLM MCP supports optional plugins for third-party tools and HTTP routes.
The core server registers built-in tools first, then loads explicitly configured
plugins. This lets local integrations add behavior without patching core tool
modules such as `server.py`, `tools/sources.py`, or `tools/downloads.py`.

Plugins are disabled by default.

## Configuration

Load plugins with a comma-separated environment variable:

```text
NOTEBOOKLM_MCP_PLUGINS=my_package.plugin,my_package.plugin:register_tools
```

Each item can be one of:

- an entry point name from the `notebooklm_tools.mcp_plugins` group;
- a Python module exposing `register(mcp)`;
- a `module:function` callable spec.

Optional settings:

```text
NOTEBOOKLM_MCP_PLUGIN_STRICT=true
NOTEBOOKLM_MCP_PLUGIN_AUTOLOAD=false
```

`NOTEBOOKLM_MCP_PLUGIN_STRICT=true` is the default. Explicit plugin load
failures stop server startup so a missing or broken integration is not silently
ignored. Set it to `false` only when best-effort loading is desired.

`NOTEBOOKLM_MCP_PLUGIN_AUTOLOAD=true` loads every installed entry point in the
`notebooklm_tools.mcp_plugins` group. Explicit `NOTEBOOKLM_MCP_PLUGINS` is
preferred for production because it is easier to audit.

## Minimal plugin module

```python
# my_package/plugin.py

def register(mcp):
    @mcp.tool()
    def plugin_status() -> dict[str, str]:
        """Return plugin health."""
        return {"status": "success"}
```

Run the MCP server with:

```text
NOTEBOOKLM_MCP_PLUGINS=my_package.plugin notebooklm-mcp
```

## Custom HTTP routes

Plugins receive the FastMCP instance, so they can register routes when they need
HTTP callbacks or short-lived download endpoints:

```python
from starlette.responses import JSONResponse


def register(mcp):
    @mcp.custom_route("/plugins/example/health", methods=["GET"])
    async def plugin_health(request):
        return JSONResponse({"status": "healthy"})
```

Plugins that expose routes are responsible for their own security model:
confirmation gates, token validation, TTLs, path validation, cleanup, and any
public-tunnel exposure controls.

## Packaging entry point

A plugin package can advertise itself through Python package metadata:

```toml
[project.entry-points."notebooklm_tools.mcp_plugins"]
chatgpt_bridge = "notebooklm_chatgpt_bridge:register"
```

Then load it explicitly:

```text
NOTEBOOKLM_MCP_PLUGINS=chatgpt_bridge notebooklm-mcp
```

## Design intent

The plugin seam is intentionally small. Core NotebookLM MCP remains responsible
for built-in NotebookLM tools and authentication. Plugins should depend on
public service-layer APIs and should avoid monkey-patching built-in tools.
