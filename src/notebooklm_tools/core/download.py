#!/usr/bin/env python3
"""Download operations mixin for NotebookLM client."""

import csv
import html as html_module
import json
import re
from pathlib import Path
from typing import Any, Callable

import httpx

from . import constants
from .base import BaseClient, logger
from .errors import (
    ArtifactDownloadError,
    ArtifactNotFoundError,
    ArtifactNotReadyError,
    ArtifactParseError,
    ClientAuthenticationError as AuthenticationError,
)


class DownloadMixin(BaseClient):
    """Mixin for artifact download operations.
    
    This mixin provides methods for downloading various artifact types:
    - Audio (MP4/MP3)
    - Video (MP4)
    - Infographic (PNG)
    - Slide Deck (PDF)
    - Report (Markdown)
    - Mind Map (JSON)
    - Data Table (CSV)
    - Quiz (JSON/Markdown/HTML)
    - Flashcards (JSON/Markdown/HTML)
    """

    # =========================================================================
    # Core Download Infrastructure
    # =========================================================================

    async def _download_url(
        self,
        url: str,
        output_path: str,
        progress_callback: Callable[[int, int], None] | None = None,
        chunk_size: int = 65536
    ) -> str:
        """Download content from a URL to a local file with streaming support.

        Features:
        - Streams file in chunks to minimize memory usage
        - Optional progress callback for UI integration
        - Per-chunk timeouts to detect stalled connections
        - Temp file usage to prevent corrupted partial downloads
        - Authentication error detection

        Args:
            url: The URL to download
            output_path: The local path to save the file
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
            chunk_size: Size of chunks to read (default 64KB)

        Returns:
            The output path

        Raises:
            ArtifactDownloadError: If download fails
            AuthenticationError: If auth redirect detected
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Use temp file to prevent corrupted partial downloads
        temp_file = output_file.with_suffix(output_file.suffix + ".tmp")

        # Build headers with auth cookies
        base_headers = getattr(self, "_PAGE_FETCH_HEADERS", {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        headers = {**base_headers, "Referer": "https://notebooklm.google.com/"}

        # Use httpx.Cookies for proper cross-domain redirect handling
        cookies = self._get_httpx_cookies()

        # Per-chunk timeouts: 10s connect, 30s per chunk read/write
        # This allows large files to download without timeout while detecting stalls
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=30.0)

        try:
            async with httpx.AsyncClient(
                cookies=cookies,
                headers=headers,
                follow_redirects=True,
                timeout=timeout
            ) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()

                    # Get total size if available
                    content_length = response.headers.get("content-length")
                    total_bytes = int(content_length) if content_length else 0

                    # Check for auth redirect before starting download
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" in content_type:
                        # Read first chunk to check for login page
                        first_chunk = b""
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            first_chunk = chunk
                            break

                        if b"<!doctype html>" in first_chunk.lower() or b"sign in" in first_chunk.lower():
                            raise AuthenticationError(
                                "Download failed: Redirected to login page. "
                                "Run 'nlm login' to refresh credentials."
                            )

                        # Not an auth error - write first chunk and continue
                        with open(temp_file, "wb") as f:
                            f.write(first_chunk)
                            bytes_downloaded = len(first_chunk)

                            if progress_callback:
                                progress_callback(bytes_downloaded, total_bytes)

                            # Continue streaming rest of file
                            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                                f.write(chunk)
                                bytes_downloaded += len(chunk)

                                if progress_callback:
                                    progress_callback(bytes_downloaded, total_bytes)
                    else:
                        # Binary content - stream directly
                        bytes_downloaded = 0
                        with open(temp_file, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                                f.write(chunk)
                                bytes_downloaded += len(chunk)

                                if progress_callback:
                                    progress_callback(bytes_downloaded, total_bytes)

            # Move temp file to final location only on success
            temp_file.rename(output_file)
            return str(output_file)

        except httpx.HTTPError as e:
            # Clean up temp file on failure
            if temp_file.exists():
                temp_file.unlink()
            raise ArtifactDownloadError(
                "file",
                details=f"HTTP error downloading from {url[:50]}...: {e}"
            ) from e
        except Exception as e:
            # Clean up temp file on failure
            if temp_file.exists():
                temp_file.unlink()
            raise ArtifactDownloadError(
                "file",
                details=f"Failed to download from {url[:50]}...: {str(e)}"
            ) from e

    def _list_raw(self, notebook_id: str) -> list[Any]:
        """Get raw artifact list for parsing download URLs."""
        # Poll params: [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        params = [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        body = self._build_request_body(self.RPC_POLL_STUDIO, params)
        url = self._build_url(self.RPC_POLL_STUDIO, f"/notebook/{notebook_id}")
        
        client = self._get_client()
        response = client.post(url, content=body)
        response.raise_for_status()
        
        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_POLL_STUDIO)
        
        if result and isinstance(result, list) and len(result) > 0:
             # Response is an array of artifacts, possibly wrapped
             return result[0] if isinstance(result[0], list) else result
        return []

    # =========================================================================
    # Binary Artifact Downloads (Audio, Video, Infographic, Slide Deck)
    # =========================================================================

    async def download_audio(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """Download an Audio Overview to a file.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the audio file (MP4/MP3).
            artifact_id: Specific artifact ID, or uses first completed audio.
            progress_callback: Optional callback(bytes_downloaded, total_bytes).

        Returns:
            The output path.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed audio (Type 1, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 4:
                if a[2] == self.STUDIO_TYPE_AUDIO and a[4] == 3:
                    candidates.append(a)

        if not candidates:
            raise ArtifactNotReadyError("audio")

        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("audio", artifact_id)
        else:
            target = candidates[0]

        # Extract URL from metadata[6][5]
        try:
            metadata = target[6]
            if not isinstance(metadata, list) or len(metadata) <= 5:
                raise ArtifactParseError("audio", details="Invalid audio metadata structure")

            media_list = metadata[5]
            if not isinstance(media_list, list) or len(media_list) == 0:
                raise ArtifactParseError("audio", details="No media URLs found in metadata")

            # Look for audio/mp4 mime type
            url = None
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "audio/mp4":
                    url = item[0]
                    break

            # Fallback to first URL if no audio/mp4 found
            if not url and len(media_list) > 0 and isinstance(media_list[0], list):
                url = media_list[0][0]

            if not url:
                raise ArtifactDownloadError("audio", details="No download URL found")

            return await self._download_url(url, output_path, progress_callback)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("audio", details=str(e)) from e

    async def download_video(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """Download a Video Overview to a file.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the video file (MP4).
            artifact_id: Specific artifact ID, or uses first completed video.
            progress_callback: Optional callback(bytes_downloaded, total_bytes).

        Returns:
            The output path.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed video (Type 3, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 4:
                if a[2] == self.STUDIO_TYPE_VIDEO and a[4] == 3:
                    candidates.append(a)

        if not candidates:
            raise ArtifactNotReadyError("video")

        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("video", artifact_id)
        else:
            target = candidates[0]

        # Extract URL from metadata[8]
        try:
            metadata = target[8]
            if not isinstance(metadata, list):
                raise ArtifactParseError("video", details="Invalid metadata structure")

            # First, find the media_list (nested list containing URLs)
            media_list = None
            for item in metadata:
                if (isinstance(item, list) and len(item) > 0 and
                    isinstance(item[0], list) and len(item[0]) > 0 and
                    isinstance(item[0][0], str) and item[0][0].startswith("http")):
                    media_list = item
                    break

            if not media_list:
                raise ArtifactDownloadError("video", details="No media URLs found in metadata")

            # Look for video/mp4 with optimal encoding (item[1] == 4 indicates priority)
            url = None
            for item in media_list:
                if isinstance(item, list) and len(item) > 2 and item[2] == "video/mp4":
                    url = item[0]
                    # Prefer URLs with priority flag (item[1] == 4)
                    if len(item) > 1 and item[1] == 4:
                        break

            # Fallback to first URL if no video/mp4 found
            if not url and len(media_list) > 0 and isinstance(media_list[0], list):
                url = media_list[0][0]

            if not url:
                raise ArtifactDownloadError("video", details="No download URL found")

            return await self._download_url(url, output_path, progress_callback)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("video", details=str(e)) from e

    async def download_infographic(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> str:
        """Download an Infographic to a file.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the PNG file.
            artifact_id: Specific artifact ID, or uses first completed infographic.
            progress_callback: Optional callback(bytes_downloaded, total_bytes).

        Returns:
            The output path.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed infographics (Type 7, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 5:
                if a[2] == self.STUDIO_TYPE_INFOGRAPHIC and a[4] == 3:
                    candidates.append(a)

        if not candidates:
            raise ArtifactNotReadyError("infographic")

        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("infographic", artifact_id)
        else:
            target = candidates[0]

        # Extract URL from target[14][2][0][1][0] (lh3.googleusercontent.com)
        try:
            if len(target) <= 14 or target[14] is None:
                raise ArtifactParseError("infographic", details="Invalid metadata structure")

            metadata = target[14]
            if not isinstance(metadata, list) or len(metadata) < 3:
                raise ArtifactParseError("infographic", details="No media data in metadata")

            media_data = metadata[2]
            if not isinstance(media_data, list) or len(media_data) == 0:
                raise ArtifactParseError("infographic", details="No media items found")

            # Navigate: media_data[0][1][0] to get URL
            media_item = media_data[0]
            if not isinstance(media_item, list) or len(media_item) < 2:
                raise ArtifactParseError("infographic", details="Invalid media item structure")

            url_data = media_item[1]
            if not isinstance(url_data, list) or len(url_data) == 0:
                raise ArtifactParseError("infographic", details="No URL data found")

            url = url_data[0]
            if not url or not isinstance(url, str):
                raise ArtifactDownloadError("infographic", details="No download URL found")

            return await self._download_url(url, output_path, progress_callback)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("infographic", details=str(e)) from e

    async def download_slide_deck(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
        file_format: str = "pdf",
    ) -> str:
        """Download a Slide Deck to a file (PDF or PPTX).

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the file.
            artifact_id: Specific artifact ID, or uses first completed slide deck.
            progress_callback: Optional callback(bytes_downloaded, total_bytes).
            file_format: "pdf" (default) or "pptx".

        Returns:
            The output path.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed slide decks (Type 8, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 5:
                if a[2] == self.STUDIO_TYPE_SLIDE_DECK and a[4] == 3:
                    candidates.append(a)

        if not candidates:
            raise ArtifactNotReadyError("slide_deck")

        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("slide_deck", artifact_id)
        else:
            target = candidates[0]

        # Extract URL from target[16]: index 3 = PDF, index 4 = PPTX
        try:
            if len(target) <= 16 or target[16] is None:
                raise ArtifactParseError("slide_deck", details="Invalid metadata structure")

            metadata = target[16]
            if file_format == "pptx":
                if not isinstance(metadata, list) or len(metadata) < 5:
                    raise ArtifactParseError("slide_deck", details="No PPTX URL found in metadata")
                url = metadata[4]
                if not url or not isinstance(url, str):
                    raise ArtifactDownloadError("slide_deck", details="No PPTX download URL found")
            else:
                if not isinstance(metadata, list) or len(metadata) < 4:
                    raise ArtifactParseError("slide_deck", details="No PDF URL found in metadata")
                url = metadata[3]
                if not url or not isinstance(url, str):
                    raise ArtifactDownloadError("slide_deck", details="No PDF download URL found")

            return await self._download_url(url, output_path, progress_callback)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("slide_deck", details=str(e)) from e

    # =========================================================================
    # Text Artifact Downloads (Report, Mind Map, Data Table)
    # =========================================================================

    def download_report(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
    ) -> str:
        """Download a report artifact as markdown.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the markdown file.
            artifact_id: Specific artifact ID, or uses first completed report.

        Returns:
            The output path where the file was saved.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed reports (Type 6, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 7:
                if a[2] == self.STUDIO_TYPE_REPORT and a[4] == 3:
                    candidates.append(a)
        
        if not candidates:
             raise ArtifactNotReadyError("report")
        
        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("report", artifact_id)
        else:
            target = candidates[0]

        try:
            # Report content is in index 7
            content_wrapper = target[7]
            markdown_content = ""
            
            if isinstance(content_wrapper, list) and len(content_wrapper) > 0:
                markdown_content = content_wrapper[0]
            elif isinstance(content_wrapper, str):
                markdown_content = content_wrapper
            
            if not isinstance(markdown_content, str):
                raise ArtifactParseError("report", details="Invalid content structure")

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(markdown_content, encoding="utf-8")
            return str(output)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("report", details=str(e)) from e

    def download_mind_map(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
    ) -> str:
        """Download a mind map as JSON.

        Mind maps are stored in the notes system, not the regular artifacts list.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the JSON file.
            artifact_id: Specific mind map ID (note ID), or uses first available.

        Returns:
            The output path where the file was saved.
        """
        # Mind maps are retrieved via list_mind_maps RPC
        params = [notebook_id]
        result = self._call_rpc(self.RPC_LIST_MIND_MAPS, params, f"/notebook/{notebook_id}")
        
        mind_maps = []
        if result and isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], list):
                 mind_maps = result[0]
        
        if not mind_maps:
            raise ArtifactNotReadyError("mind_map")

        target = None
        if artifact_id:
            target = next((mm for mm in mind_maps if isinstance(mm, list) and mm[0] == artifact_id), None)
            if not target:
                raise ArtifactNotFoundError(artifact_id, artifact_type="mind_map")
        else:
            target = mind_maps[0]

        try:
            # Mind map JSON is stringified in target[1][1]
            if len(target) > 1 and isinstance(target[1], list) and len(target[1]) > 1:
                 json_string = target[1][1]
                 if isinstance(json_string, str):
                     json_data = json.loads(json_string)
                     
                     output = Path(output_path)
                     output.parent.mkdir(parents=True, exist_ok=True)
                     output.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
                     return str(output)
            
            raise ArtifactParseError("mind_map", details="Invalid structure")

        except (IndexError, TypeError, json.JSONDecodeError, AttributeError) as e:
            raise ArtifactParseError("mind_map", details=str(e)) from e

    @staticmethod
    def _extract_cell_text(cell: Any, _depth: int = 0) -> str:
        """Recursively extract text from a nested data table cell structure.

        Data table cells have deeply nested arrays with position markers (integers)
        and text content (strings). This function traverses the structure and
        concatenates all text fragments found.

        Features:
        - Depth tracking to prevent infinite recursion (max 100 levels)
        - Handles None values gracefully
        - Strips whitespace from extracted text
        - Type validation at each level

        Args:
            cell: The cell data structure (can be str, int, list, or other)
            _depth: Internal recursion depth counter for safety

        Returns:
            Extracted text string, stripped of leading/trailing whitespace
        """
        # Safety: prevent infinite recursion
        if _depth > 100:
            return ""

        # Handle different types
        if cell is None:
            return ""
        if isinstance(cell, str):
            return cell.strip()
        if isinstance(cell, (int, float)):
            return ""  # Position markers are numeric
        if isinstance(cell, list):
            # Recursively extract from all list items
            parts = []
            for item in cell:
                text = DownloadMixin._extract_cell_text(item, _depth + 1)
                if text:
                    parts.append(text)
            return " ".join(parts) if parts else ""

        # Unknown type - convert to string as fallback
        return str(cell).strip()

    def _parse_data_table(
        self,
        raw_data: list,
        validate_columns: bool = True
    ) -> tuple[list[str], list[list[str]]]:
        """Parse rich-text data table into headers and rows.

        Features:
        - Validates structure at each navigation step with clear error messages
        - Optional column count validation across all rows
        - Handles missing/empty cells gracefully
        - Provides detailed error context for debugging

        Structure: raw_data[0][0][0][0][4][2] contains the rows array where:
        - [0][0][0][0] navigates through wrapper layers
        - [4] contains the table content section [type, flags, rows_array]
        - [2] is the actual rows array

        Each row: [start_pos, end_pos, [cell1, cell2, ...]]
        Each cell: deeply nested with position markers mixed with text

        Args:
            raw_data: The raw data table metadata from artifact[18]
            validate_columns: If True, ensures all rows have same column count as headers

        Returns:
            Tuple of (headers, rows) where:
            - headers: List of column names
            - rows: List of data rows (each row is a list matching header length)

        Raises:
            ArtifactParseError: With detailed context if parsing fails
        """
        # Validate and navigate structure with clear error messages
        try:
            if not isinstance(raw_data, list) or len(raw_data) == 0:
                raise ArtifactParseError(
                    "data_table",
                    details="Invalid raw_data: expected non-empty list at artifact[18]"
                )

            # Navigate: raw_data[0]
            layer1 = raw_data[0]
            if not isinstance(layer1, list) or len(layer1) == 0:
                raise ArtifactParseError(
                    "data_table",
                    details="Invalid structure at raw_data[0]: expected non-empty list"
                )

            # Navigate: [0][0]
            layer2 = layer1[0]
            if not isinstance(layer2, list) or len(layer2) == 0:
                raise ArtifactParseError(
                    "data_table",
                    details="Invalid structure at raw_data[0][0]: expected non-empty list"
                )

            # Navigate: [0][0][0]
            layer3 = layer2[0]
            if not isinstance(layer3, list) or len(layer3) == 0:
                raise ArtifactParseError(
                    "data_table",
                    details="Invalid structure at raw_data[0][0][0]: expected non-empty list"
                )

            # Navigate: [0][0][0][0]
            layer4 = layer3[0]
            if not isinstance(layer4, list) or len(layer4) < 5:
                raise ArtifactParseError(
                    "data_table",
                    details=f"Invalid structure at raw_data[0][0][0][0]: expected list with at least 5 elements, got {len(layer4) if isinstance(layer4, list) else type(layer4).__name__}"
                )

            # Navigate: [0][0][0][0][4] - table content section
            table_section = layer4[4]
            if not isinstance(table_section, list) or len(table_section) < 3:
                raise ArtifactParseError(
                    "data_table",
                    details=f"Invalid table section at raw_data[0][0][0][0][4]: expected list with at least 3 elements, got {len(table_section) if isinstance(table_section, list) else type(table_section).__name__}"
                )

            # Navigate: [0][0][0][0][4][2] - rows array
            rows_array = table_section[2]
            if not isinstance(rows_array, list):
                raise ArtifactParseError(
                    "data_table",
                    details=f"Invalid rows array at raw_data[0][0][0][0][4][2]: expected list, got {type(rows_array).__name__}"
                )

            if not rows_array:
                raise ArtifactParseError(
                    "data_table",
                    details="Empty rows array - data table contains no data"
                )

        except IndexError as e:
            raise ArtifactParseError(
                "data_table",
                details=f"Structure navigation failed - table may be corrupted or in unexpected format: {e}"
            ) from e

        # Extract headers and rows
        headers: list[str] = []
        rows: list[list[str]] = []
        skipped_rows = 0

        for i, row_section in enumerate(rows_array):
            # Validate row format: [start_pos, end_pos, [cell_array]]
            if not isinstance(row_section, list):
                skipped_rows += 1
                continue

            if len(row_section) < 3:
                skipped_rows += 1
                continue

            cell_array = row_section[2]
            if not isinstance(cell_array, list):
                skipped_rows += 1
                continue

            # Extract text from each cell
            row_values = [self._extract_cell_text(cell) for cell in cell_array]

            # First row is headers
            if i == 0:
                headers = row_values
                if not headers or all(not h for h in headers):
                    raise ArtifactParseError(
                        "data_table",
                        details="First row (headers) is empty - table must have column headers"
                    )
            else:
                # Validate column count if requested
                if validate_columns and len(row_values) != len(headers):
                    # Pad or truncate to match header length
                    if len(row_values) < len(headers):
                        row_values.extend([""] * (len(headers) - len(row_values)))
                    else:
                        row_values = row_values[:len(headers)]

                rows.append(row_values)

        # Final validation
        if not headers:
            raise ArtifactParseError(
                "data_table",
                details="Failed to extract headers - first row may be malformed"
            )

        if not rows:
            raise ArtifactParseError(
                "data_table",
                details=f"No data rows extracted (skipped {skipped_rows} malformed rows)"
            )

        return headers, rows

    def download_data_table(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
    ) -> str:
        """Download a data table as CSV.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the CSV file.
            artifact_id: Specific artifact ID, or uses first completed data table.

        Returns:
            The output path where the file was saved.
        """
        artifacts = self._list_raw(notebook_id)

        # Filter for completed data tables (Type 9, Status 3)
        candidates = []
        for a in artifacts:
            if isinstance(a, list) and len(a) > 18:
                if a[2] == self.STUDIO_TYPE_DATA_TABLE and a[4] == 3:
                    candidates.append(a)

        if not candidates:
            raise ArtifactNotReadyError("data_table")

        target = None
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError("data_table", artifact_id)
        else:
            target = candidates[0]

        try:
            # Data is at index 18
            raw_data = target[18]
            headers, rows = self._parse_data_table(raw_data)

            # Write to CSV
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

            with open(output, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

            return str(output)

        except (IndexError, TypeError, AttributeError) as e:
            raise ArtifactParseError("data_table", details=str(e)) from e

    # =========================================================================
    # Interactive Artifact Downloads (Quiz, Flashcards)
    # =========================================================================

    def _get_artifact_content(self, notebook_id: str, artifact_id: str) -> str | None:
        """Fetch artifact HTML content for quiz/flashcard types.

        Args:
            notebook_id: The notebook ID.
            artifact_id: The artifact ID.

        Returns:
            HTML content string, or None if not found.

        Raises:
            ArtifactDownloadError: If API response structure is unexpected.
        """
        result = self._call_rpc(
            self.RPC_GET_INTERACTIVE_HTML,
            [artifact_id],
            f"/notebook/{notebook_id}"
        )

        if not result:
            logger.debug(f"Empty response for artifact {artifact_id}")
            return None

        # Response structure: result[0] contains artifact data
        # HTML content is at result[0][9][0]
        try:
            if not isinstance(result, list) or len(result) == 0:
                logger.warning(f"Unexpected response type for {artifact_id}: {type(result)}")
                return None

            data = result[0]
            if not isinstance(data, list):
                logger.warning(f"Unexpected artifact data type: {type(data)}")
                return None

            if len(data) <= 9:
                logger.warning(f"Artifact data too short (len={len(data)}), expected index 9")
                return None

            html_container = data[9]
            if not html_container or not isinstance(html_container, list) or len(html_container) == 0:
                logger.debug(f"No HTML content in artifact {artifact_id}")
                return None

            return html_container[0]

        except (IndexError, TypeError) as e:
            logger.error(f"Error parsing artifact content for {artifact_id}: {e}")
            # Log truncated response for debugging
            result_preview = str(result)[:500] if result else "None"
            logger.debug(f"Response preview: {result_preview}...")
            raise ArtifactDownloadError(
                "interactive",
                details=f"Unexpected API response structure: {e}"
            ) from e

    def _extract_app_data(self, html_content: str) -> dict:
        """Extract JSON app data from interactive HTML.

        Quiz and flashcard HTML contains embedded JSON in a data-app-data
        attribute with HTML-encoded content (&quot; for quotes).

        Tries multiple extraction patterns for robustness:
        1. data-app-data attribute (primary)
        2. <script id="application-data"> tag (fallback)
        3. Other common patterns

        Args:
            html_content: The HTML content string.

        Returns:
            Parsed JSON data as dict.

        Raises:
            ArtifactParseError: If data cannot be extracted or parsed.
        """
        # Pattern 1: data-app-data attribute (most common)
        # Handle both single and multiline with greedy matching
        match = re.search(r'data-app-data="([^"]*(?:\\"[^"]*)*)"', html_content, re.DOTALL)
        if match:
            encoded_json = match.group(1)
            decoded_json = html_module.unescape(encoded_json)

            try:
                data = json.loads(decoded_json)
                logger.debug("Extracted app data using data-app-data attribute")
                return data
            except json.JSONDecodeError as e:
                # Log the error but try other patterns
                logger.debug(f"Failed to parse data-app-data JSON: {e}")
                logger.debug(f"JSON preview: {decoded_json[:200]}...")

        # Pattern 2: <script id="application-data"> tag
        match = re.search(
            r'<script[^>]+id=["\']application-data["\'][^>]*>(.*?)</script>',
            html_content,
            re.DOTALL
        )
        if match:
            try:
                data = json.loads(match.group(1))
                logger.debug("Extracted app data using script tag")
                return data
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse script tag JSON: {e}")

        # Pattern 3: data-state or data-config attributes (additional fallback)
        for attr in ['data-state', 'data-config', 'data-initial-state']:
            match = re.search(rf'{attr}="([^"]*(?:\\"[^"]*)*)"', html_content, re.DOTALL)
            if match:
                encoded_json = match.group(1)
                decoded_json = html_module.unescape(encoded_json)
                try:
                    data = json.loads(decoded_json)
                    logger.debug(f"Extracted app data using {attr} attribute")
                    return data
                except json.JSONDecodeError:
                    continue

        # No patterns matched - provide detailed error
        html_preview = html_content[:500] if html_content else "Empty"
        logger.error(f"Failed to extract app data. HTML preview: {html_preview}...")

        raise ArtifactParseError(
            "interactive",
            details=(
                "Could not extract JSON data from HTML. "
                "Tried: data-app-data, script#application-data, data-state, data-config"
            )
        )

    @staticmethod
    def _format_quiz_markdown(title: str, questions: list[dict]) -> str:
        """Format quiz as markdown.

        Args:
            title: Quiz title.
            questions: List of question dicts with 'question', 'answerOptions', 'hint'.

        Returns:
            Formatted markdown string.
        """
        lines = [f"# {title}", ""]

        for i, q in enumerate(questions, 1):
            lines.append(f"## Question {i}")
            lines.append(q.get("question", ""))
            lines.append("")

            for opt in q.get("answerOptions", []):
                marker = "[x]" if opt.get("isCorrect") else "[ ]"
                lines.append(f"- {marker} {opt.get('text', '')}")

            if q.get("hint"):
                lines.append("")
                lines.append(f"**Hint:** {q['hint']}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_flashcards_markdown(title: str, cards: list[dict]) -> str:
        """Format flashcards as markdown.

        Args:
            title: Flashcard deck title.
            cards: List of card dicts with 'f' (front) and 'b' (back).

        Returns:
            Formatted markdown string.
        """
        lines = [f"# {title}", ""]

        for i, card in enumerate(cards, 1):
            front = card.get("f", "")
            back = card.get("b", "")

            lines.append(f"## Card {i}")
            lines.append("")
            lines.append(f"**Front:** {front}")
            lines.append("")
            lines.append(f"**Back:** {back}")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_interactive_content(
        self,
        app_data: dict,
        title: str,
        output_format: str,
        html_content: str,
        is_quiz: bool,
    ) -> str:
        """Format quiz or flashcard content for output.

        Args:
            app_data: Parsed JSON data from HTML.
            title: Artifact title.
            output_format: Output format - json, markdown, or html.
            html_content: Original HTML content.
            is_quiz: True for quiz, False for flashcards.

        Returns:
            Formatted content string.
        """
        if output_format == "html":
            return html_content

        if is_quiz:
            questions = app_data.get("quiz", [])
            if output_format == "markdown":
                return self._format_quiz_markdown(title, questions)
            return json.dumps({"title": title, "questions": questions}, indent=2)

        # Flashcards
        cards = app_data.get("flashcards", [])
        if output_format == "markdown":
            return self._format_flashcards_markdown(title, cards)

        # Normalize JSON format: {"f": "...", "b": "..."} -> {"front": "...", "back": "..."}
        normalized = [{"front": c.get("f", ""), "back": c.get("b", "")} for c in cards]
        return json.dumps({"title": title, "cards": normalized}, indent=2)

    async def _download_interactive_artifact(
        self,
        notebook_id: str,
        output_path: str,
        artifact_type: str,
        is_quiz: bool,
        artifact_id: str | None = None,
        output_format: str = "json",
    ) -> str:
        """Shared implementation for downloading quiz/flashcard artifacts.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the file.
            artifact_type: Human-readable type for error messages ("quiz" or "flashcards").
            is_quiz: True for quiz, False for flashcards.
            artifact_id: Specific artifact ID, or uses first completed artifact.
            output_format: Output format - json, markdown, or html.

        Returns:
            The output path where the file was saved.

        Raises:
            ValueError: If invalid output_format.
            ArtifactNotReadyError: If no completed artifact found.
            ArtifactParseError: If content parsing fails.
            ArtifactDownloadError: If content fetch fails.
        """
        # Validate format
        valid_formats = ("json", "markdown", "html")
        if output_format not in valid_formats:
            raise ValueError(
                f"Invalid output_format: {output_format!r}. "
                f"Use one of: {', '.join(valid_formats)}"
            )

        # Get all artifacts and filter for completed interactive artifacts
        artifacts = self._list_raw(notebook_id)

        # Type 4 (STUDIO_TYPE_FLASHCARDS) covers both quizzes and flashcards
        # Status 3 = completed
        candidates = [
            a for a in artifacts
            if isinstance(a, list) and len(a) > 4
            and a[2] == self.STUDIO_TYPE_FLASHCARDS
            and a[4] == 3
        ]

        if not candidates:
            raise ArtifactNotReadyError(artifact_type)

        # Select artifact by ID or use most recent
        if artifact_id:
            target = next((a for a in candidates if a[0] == artifact_id), None)
            if not target:
                raise ArtifactNotReadyError(artifact_type, artifact_id)
        else:
            target = candidates[0]  # Most recent

        # Fetch HTML content
        html_content = self._get_artifact_content(notebook_id, target[0])
        if not html_content:
            raise ArtifactDownloadError(
                artifact_type,
                details="Failed to fetch HTML content from API"
            )

        # Extract and parse embedded JSON
        try:
            app_data = self._extract_app_data(html_content)
        except ArtifactParseError:
            raise  # Re-raise as-is
        except (ValueError, json.JSONDecodeError) as e:
            raise ArtifactParseError(artifact_type, details=str(e)) from e

        # Get title from artifact metadata
        default_title = f"Untitled {artifact_type.title()}"
        title = target[1] if len(target) > 1 and target[1] else default_title

        # Format content
        content = self._format_interactive_content(
            app_data, title, output_format, html_content, is_quiz
        )

        # Write to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")

        logger.info(f"Downloaded {artifact_type} to {output} ({output_format} format)")
        return str(output)

    async def download_quiz(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        output_format: str = "json",
    ) -> str:
        """Download quiz artifact.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the file.
            artifact_id: Specific artifact ID, or uses first completed quiz.
            output_format: Output format - json, markdown, or html (default: json).

        Returns:
            The output path where the file was saved.

        Raises:
            ValueError: If invalid output_format.
            ArtifactNotReadyError: If no completed quiz found.
            ArtifactParseError: If content parsing fails.
        """
        return await self._download_interactive_artifact(
            notebook_id=notebook_id,
            output_path=output_path,
            artifact_type="quiz",
            is_quiz=True,
            artifact_id=artifact_id,
            output_format=output_format,
        )

    async def download_flashcards(
        self,
        notebook_id: str,
        output_path: str,
        artifact_id: str | None = None,
        output_format: str = "json",
    ) -> str:
        """Download flashcard deck artifact.

        Args:
            notebook_id: The notebook ID.
            output_path: Path to save the file.
            artifact_id: Specific artifact ID, or uses first completed flashcard deck.
            output_format: Output format - json, markdown, or html (default: json).

        Returns:
            The output path where the file was saved.

        Raises:
            ValueError: If invalid output_format.
            ArtifactNotReadyError: If no completed flashcards found.
            ArtifactParseError: If content parsing fails.
        """
        return await self._download_interactive_artifact(
            notebook_id=notebook_id,
            output_path=output_path,
            artifact_type="flashcards",
            is_quiz=False,
            artifact_id=artifact_id,
            output_format=output_format,
        )
