# Security Standards

## Mandatory — no exceptions

- No credentials, API keys, tokens, cookies, or secrets in source code
- No credentials in `ai/` files, comments, or commit messages
- Use environment variables or `~/.notebooklm-mcp-cli/config.toml` for all config
- Input validation on all user-supplied data before use
- Log security events; never log sensitive data or credentials
- Auth tokens must not appear in exception messages or log output

## Credential and secret storage

- Never commit cookies, GCP tokens, or API keys to the repo — in any file
- Personal auth stored in `~/.notebooklm-mcp-cli/profiles/<name>/auth.json` (chmod 0600)
- Enterprise auth via `gcloud` — token fetched at runtime, never stored by this project
- `config.toml` stores mode, project_id, location — never tokens
- Rotate any credential that is accidentally committed immediately — assume it is compromised

## Project-specific security rules

- **Subprocess calls**: Always use list-form args, never `shell=True`
  ```python
  # CORRECT
  subprocess.run(["gcloud", "auth", "print-access-token"], ...)
  # NEVER
  subprocess.run("gcloud auth print-access-token", shell=True)
  ```
- **ID validation**: All enterprise resource IDs validated with `_validate_id()` regex
  before interpolation into REST paths (`^[a-zA-Z0-9\-]+$`)
- **Path traversal**: File upload paths validated — no `../` traversal allowed
- **SSRF**: URL paywall checker blocks private IPs (loopback, RFC-1918, 169.254.x.x)
  using `ipaddress` module before any outbound HTTP request
- **Error messages**: Enterprise client strips auth headers from all HTTP exceptions
- **CDP port**: Chrome DevTools Protocol only binds to `127.0.0.1` — never exposed to network

## Dependency security

- Pin all dependency versions in `uv.lock`
- Run `uvx pip-audit` before each release
- Address critical and high vulnerabilities before merging to main

## Code review security checklist

Before merging anything that touches authentication, URLs, file paths, or subprocess:
- [ ] No hardcoded credentials, tokens, or cookies
- [ ] Subprocess calls use list args (not shell=True)
- [ ] User-supplied IDs validated before use in API paths
- [ ] User-supplied file paths validated for traversal
- [ ] User-supplied URLs checked for SSRF (private IP ranges)
- [ ] Error messages do not expose auth headers or token values
- [ ] No credentials in `ai/` files or test fixtures
