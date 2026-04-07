## What does this PR do?

<!-- Brief description of the change and why it's needed -->

## Type of change

- [ ] Bug fix — personal mode
- [ ] Bug fix — enterprise mode
- [ ] New feature
- [ ] Chore / dependency update / CI
- [ ] Documentation

## Checklist

- [ ] `uv run pytest -m "not e2e"` passes locally
- [ ] `uv run --extra dev ruff check .` is clean
- [ ] `uv run --extra dev ruff format --check .` is clean
- [ ] No credentials, tokens, or GCP project IDs in the diff
- [ ] If this touches enterprise code: tested against a real GCP project (or clearly marked as untested)
- [ ] If this is a new feature: docs or README updated where relevant

## Related issues

<!-- Closes #123 -->
