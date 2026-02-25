# NotebookLM MCP Code Tour

**Last Updated**: 2026-01-10
**Version**: 0.1.0

Navigate the C021 codebase efficiently.

## Quick Reference

| I want to... | Look at... |
|--------------|------------|
| Add a new MCP tool | `src/notebooklm_mcp/server.py` |
| Add a new API method | `src/notebooklm_mcp/api_client.py` |
| Fix auth issues | `src/notebooklm_mcp/auth.py` |
| Modify auth CLI | `src/notebooklm_mcp/auth_cli.py` |
| Understand API format | `docs/API_REFERENCE.md` |
| Test tools | `docs/MCP_TEST_PLAN.md` |
| Debug issues | `docs/TROUBLESHOOTING.md` |

## Directory Map

```
C021_notebooklm-mcp/
├── src/notebooklm_mcp/           # Core Python package
│   ├── __init__.py               # Package version (0.1.0)
│   ├── server.py                 # FastMCP server (31 tools)
│   ├── api_client.py             # NotebookLM API client (~110KB)
│   ├── auth.py                   # Token caching/validation
│   ├── auth_cli.py               # Chrome-based auth CLI
│   └── doc_refresh/              # Doc-refresh Ralph loop module
│       ├── __init__.py
│       ├── canonical_docs.yaml   # Tiered doc manifest
│       ├── notebook_map.template.yaml  # Seed structure for runtime map
│       └── PROMPT.md             # Ralph loop prompt
│
├── ~/.config/notebooklm-mcp/     # Runtime doc-refresh state (local machine)
│   ├── notebook_map.yaml         # Repo → Notebook mapping (mutable)
│   └── sync_receipts/*.json      # Sync audit receipts
│
├── docs/                         # Reference documentation
│   ├── API_REFERENCE.md          # Reverse-engineered API details
│   ├── AUTHENTICATION.md         # Auth guide
│   ├── TROUBLESHOOTING.md        # Common issues
│   ├── MCP_TEST_PLAN.md          # Tool test cases
│   ├── KNOWN_ISSUES.md           # Known bugs
│   ├── media/                    # Images (header.jpeg)
│   └── doc_refresh/              # Doc-refresh epic docs
│       ├── EPIC.md
│       ├── INTERFACES.md
│       └── PHASE_*.md
│
├── skills/                       # Claude Code skills
│   └── doc-refresh/
│       └── skill.md              # /doc-refresh command
│
├── tests/                        # Test suite
│   └── test_*.py                 # Pytest tests
│
├── 00_admin/                     # Administrative (audit exceptions)
├── 10_docs/                      # Working agreements
├── 20_receipts/                  # Betty Protocol receipts
│
├── pyproject.toml                # Python project config (uv/hatch)
├── README.md                     # User documentation
├── CLAUDE.md                     # Claude Code guidance
├── META.yaml                     # Project metadata
└── CHANGELOG.md                  # Version history
```

## Key Entry Points

### MCP Server (`src/notebooklm_mcp/server.py`)

```python
# FastMCP server initialization
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notebooklm-mcp")

# Tool definition example
@mcp.tool()
async def notebook_list(
    max_results: int = 100,
    compact: bool = True
) -> dict:
    """List all notebooks."""
    client = get_client()
    notebooks = await client.list_notebooks()
    return format_response(notebooks, compact)
```

### API Client (`src/notebooklm_mcp/api_client.py`)

```python
# Batchexecute RPC call
async def _make_request(self, rpc_id: str, params: list) -> dict:
    """Make a batchexecute RPC request."""
    data = {
        "f.req": json.dumps([[[rpc_id, json.dumps(params), None, "generic"]]])
    }
    response = await self.client.post(BATCHEXECUTE_URL, data=data)
    return self._parse_response(response.text)

# Example method
async def list_notebooks(self) -> list:
    """List all notebooks."""
    return await self._make_request("wJbB3c", [])
```

### Auth System (`src/notebooklm_mcp/auth.py`)

```python
# Token cache location
AUTH_FILE = Path.home() / ".notebooklm-mcp" / "auth.json"

# Load cached tokens
def load_auth() -> dict:
    """Load cached auth tokens."""
    if AUTH_FILE.exists():
        return json.loads(AUTH_FILE.read_text())
    return {}

# Auto-extract CSRF from page
async def extract_csrf_token(page_content: str) -> str:
    """Extract CSRF token from NotebookLM page."""
    # Parse HTML for token
```

### Auth CLI (`src/notebooklm_mcp/auth_cli.py`)

```python
# Entry point
def main():
    """notebooklm-mcp-auth CLI entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", nargs="?", const=True)
    args = parser.parse_args()

    if args.file:
        file_mode(args.file)
    else:
        auto_mode()
```

## Configuration

### Package Version (`src/notebooklm_mcp/__init__.py`)

```python
__version__ = "0.1.0"
```

### Project Config (`pyproject.toml`)

```toml
[project]
name = "notebooklm-mcp-server"
version = "0.1.0"
requires-python = ">=3.11"

[project.scripts]
notebooklm-mcp = "notebooklm_mcp.server:main"
notebooklm-mcp-auth = "notebooklm_mcp.auth_cli:main"
```

## Common Patterns

### Adding a New MCP Tool

1. **Add API method** in `api_client.py`:
```python
async def new_feature(self, notebook_id: str, param: str) -> dict:
    return await self._make_request("RPC_ID", [notebook_id, param])
```

2. **Add tool** in `server.py`:
```python
@mcp.tool()
async def new_feature(notebook_id: str, param: str) -> dict:
    """Tool description."""
    client = get_client()
    return await client.new_feature(notebook_id, param)
```

3. **Document RPC ID** in `docs/API_REFERENCE.md`
4. **Add test case** in `docs/MCP_TEST_PLAN.md`

### Confirmation Pattern

```python
@mcp.tool()
async def dangerous_operation(
    notebook_id: str,
    confirm: bool = False
) -> dict:
    """Operation requiring confirmation."""
    if not confirm:
        return {
            "status": "confirm_required",
            "message": "Set confirm=True to proceed"
        }

    client = get_client()
    return await client.dangerous_operation(notebook_id)
```

### Response Formatting

```python
def format_notebook(notebook: dict, compact: bool) -> dict:
    """Format notebook for MCP response."""
    if compact:
        return {
            "id": notebook["id"],
            "title": notebook["title"],
            "source_count": len(notebook.get("sources", []))
        }
    return notebook  # Full details
```

## Development Commands

```bash
# Install for development
uv tool install .

# Reinstall after changes (always clean cache!)
uv cache clean && uv tool install --force .

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_file.py::test_function -v
```

## Test Files

| Test File | Coverage |
|-----------|----------|
| `tests/test_*.py` | Unit tests for modules |
| `docs/MCP_TEST_PLAN.md` | Manual integration tests |

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [OPERATIONS.md](OPERATIONS.md) - Day-to-day operation
- [../API_REFERENCE.md](../API_REFERENCE.md) - API details
- [../MCP_TEST_PLAN.md](../MCP_TEST_PLAN.md) - Test cases
