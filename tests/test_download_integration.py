"""Integration tests for Download functionalities.

Targeting Notebook: 4085e211-fdb0-4802-b973-b43b9f99b6f7
This notebook is expected to contain all studio artifacts (Audio, Video, etc.).

Run with: NOTEBOOKLM_E2E=1 pytest tests/test_download_integration.py -v
"""

import os
import shutil
from pathlib import Path

import pytest

from notebooklm_tools.core.client import NotebookLMClient
from notebooklm_tools.core.errors import ArtifactNotReadyError

# Target notebook ID provided by user
NOTEBOOK_ID = "4085e211-fdb0-4802-b973-b43b9f99b6f7"

pytestmark = pytest.mark.skipif(
    not os.environ.get("NOTEBOOKLM_E2E"),
    reason="Integration tests disabled. Set NOTEBOOKLM_E2E=1 to run.",
)


@pytest.fixture(scope="module")
def client():
    """Create a client with cached credentials."""
    from notebooklm_tools.core.auth import load_cached_tokens

    tokens = load_cached_tokens()
    if not tokens:
        pytest.skip("No cached credentials. Run 'nlm login' first.")

    return NotebookLMClient(
        cookies=tokens.cookies,
        csrf_token=tokens.csrf_token,
        session_id=tokens.session_id,
    )


@pytest.fixture(scope="module")
def output_dir():
    """Create a temporary output directory."""
    path = Path("tests/output")
    path.mkdir(parents=True, exist_ok=True)
    yield path
    # Cleanup
    shutil.rmtree(path, ignore_errors=True)


class TestClientDownloads:
    """Test client download methods directly."""

    def test_download_report(self, client, output_dir):
        output = output_dir / "report.md"
        path = client.download_report(NOTEBOOK_ID, str(output))
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0
        assert output.read_text().startswith("#")  # Markdown header

    def test_download_audio(self, client, output_dir):
        output = output_dir / "audio.mp4"
        try:
            path = client.download_audio(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Audio artifact not ready")

    def test_download_video(self, client, output_dir):
        output = output_dir / "video.mp4"
        try:
            path = client.download_video(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Video artifact not ready")

    def test_download_infographic(self, client, output_dir):
        output = output_dir / "infographic.png"
        try:
            path = client.download_infographic(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Infographic artifact not ready")

    def test_download_slide_deck(self, client, output_dir):
        output = output_dir / "slides.pdf"
        try:
            path = client.download_slide_deck(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Slide deck artifact not ready")

    def test_download_mind_map(self, client, output_dir):
        output = output_dir / "mindmap.json"
        try:
            path = client.download_mind_map(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Mind map artifact not ready")

    def test_download_data_table(self, client, output_dir):
        output = output_dir / "table.csv"
        try:
            path = client.download_data_table(NOTEBOOK_ID, str(output))
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
        except ArtifactNotReadyError:
            pytest.skip("Data table artifact not ready")


@pytest.fixture(scope="module")
def auth_check():
    """Check if authentication is available for CLI."""
    from notebooklm_tools.core.auth import load_cached_tokens

    if not load_cached_tokens():
        pytest.skip("No cached credentials for CLI tests")


class TestCLIDownloads:
    """Test CLI download commands."""

    def test_cli_download_report(self, output_dir, auth_check):
        import subprocess

        output = output_dir / "cli_report.md"
        result = subprocess.run(
            ["nlm", "download", "report", NOTEBOOK_ID, "--output", str(output)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "not ready" in result.stderr:
                pytest.skip("Report not ready")
            if "No authentication found" in result.stdout:
                pytest.skip("CLI reported no authentication")

            # Fail with details
            raise AssertionError(
                f"CLI failed (code {result.returncode}): {result.stderr}\nStdout: {result.stdout}"
            )

        assert result.returncode == 0
        assert output.exists()


class TestMCPDownloads:
    """Test MCP tool functions."""

    async def test_mcp_download_report(self, output_dir):
        from notebooklm_tools.core.auth import load_cached_tokens
        from notebooklm_tools.mcp.tools.downloads import download_artifact

        if not load_cached_tokens():
            pytest.skip("No cached credentials")

        output = output_dir / "mcp_report.md"
        result = await download_artifact(
            notebook_id=NOTEBOOK_ID, artifact_type="report", output_path=str(output)
        )

        if result.get("status") == "error":
            if "not ready" in str(result.get("error")):
                pytest.skip("Report not ready")
            pytest.fail(f"MCP Tool failed: {result.get('error')}")

        assert result["status"] == "success"
        assert Path(result["path"]).exists()
