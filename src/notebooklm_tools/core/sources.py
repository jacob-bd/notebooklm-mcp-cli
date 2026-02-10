"""SourceMixin - Source management operations.

This mixin provides source-related operations:
- check_source_freshness: Check if Drive source is up-to-date
- sync_drive_source: Sync a Drive source with latest content
- delete_source: Delete a source permanently
- get_notebook_sources_with_types: Get sources with type info
- add_url_source: Add URL/YouTube as source
- add_text_source: Add pasted text as source
- add_drive_source: Add Google Drive document as source
- upload_file: Upload local file via Chrome automation
- get_source_guide: Get AI-generated summary and keywords
- get_source_fulltext: Get raw text content of a source

HTTP resumable upload implementation adapted from notebooklm-py.
"""

from pathlib import Path
import time
from typing import Any

import httpx

from .base import BaseClient, SOURCE_ADD_TIMEOUT
from . import constants
from .exceptions import FileUploadError, FileValidationError
from .retry import execute_with_retry


class SourceMixin(BaseClient):
    """Mixin for source management operations.
    
    This class inherits from BaseClient and provides all source-related
    operations. It is designed to be composed with other mixins via
    multiple inheritance in the final NotebookLMClient class.
    """

    # Source processing status codes
    SOURCE_STATUS_PROCESSING = 1
    SOURCE_STATUS_READY = 2
    SOURCE_STATUS_ERROR = 3
    SOURCE_STATUS_PREPARING = 5

    def wait_for_source_ready(
        self,
        notebook_id: str,
        source_id: str,
        timeout: float = 120.0,
        poll_interval: float = 3.0,
    ) -> dict:
        """Wait for a source to finish processing.
        
        Polls the source status until it becomes READY or times out.
        
        Args:
            notebook_id: Notebook containing the source
            source_id: Source to wait for
            timeout: Max seconds to wait (default 120)
            poll_interval: Seconds between status checks (default 3)
            
        Returns:
            The source dict with status='ready'
            
        Raises:
            TimeoutError: If source doesn't become ready within timeout
            RuntimeError: If source processing fails
        """
        start = time.time()
        
        while time.time() - start < timeout:
            sources = self.get_notebook_sources_with_types(notebook_id)
            for src in sources:
                if src.get("id") == source_id:
                    status = src.get("status")
                    if status == self.SOURCE_STATUS_READY:
                        return src
                    if status == self.SOURCE_STATUS_ERROR:
                        raise RuntimeError(f"Source {source_id} failed to process")
                    break
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Source {source_id} not ready after {timeout}s")

    def check_source_freshness(self, source_id: str) -> bool | None:
        """Check if a Drive source is fresh (up-to-date with Google Drive)."""
        client = self._get_client()

        params = [None, [source_id], [2]]
        body = self._build_request_body(self.RPC_CHECK_FRESHNESS, params)
        url = self._build_url(self.RPC_CHECK_FRESHNESS)

        def _do_request():
            resp = client.post(url, content=body)
            resp.raise_for_status()
            return resp
        response = execute_with_retry(_do_request)

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CHECK_FRESHNESS)

        # true = fresh, false = stale
        if result and isinstance(result, list) and len(result) > 0:
            inner = result[0] if result else []
            if isinstance(inner, list) and len(inner) >= 2:
                return inner[1]  # true = fresh, false = stale
        return None

    def sync_drive_source(self, source_id: str) -> dict | None:
        """Sync a Drive source with the latest content from Google Drive."""
        client = self._get_client()

        # Sync params: [null, ["source_id"], [2]]
        params = [None, [source_id], [2]]
        body = self._build_request_body(self.RPC_SYNC_DRIVE, params)
        url = self._build_url(self.RPC_SYNC_DRIVE)

        def _do_request():
            resp = client.post(url, content=body)
            resp.raise_for_status()
            return resp
        response = execute_with_retry(_do_request)

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_SYNC_DRIVE)

        if result and isinstance(result, list) and len(result) > 0:
            source_data = result[0] if result else []
            if isinstance(source_data, list) and len(source_data) >= 3:
                source_id_result = source_data[0][0] if source_data[0] else None
                title = source_data[1] if len(source_data) > 1 else "Unknown"
                metadata = source_data[2] if len(source_data) > 2 else []

                synced_at = None
                if isinstance(metadata, list) and len(metadata) > 3:
                    sync_info = metadata[3]
                    if isinstance(sync_info, list) and len(sync_info) > 1:
                        ts = sync_info[1]
                        if isinstance(ts, list) and len(ts) > 0:
                            synced_at = ts[0]

                return {
                    "id": source_id_result,
                    "title": title,
                    "synced_at": synced_at,
                }
        return None

    def delete_source(self, source_id: str) -> bool:
        """Delete a source from a notebook permanently.

        WARNING: This action is IRREVERSIBLE. The source will be permanently
        deleted from the notebook.

        Args:
            source_id: The source UUID to delete

        Returns:
            True on success, False on failure
        """
        client = self._get_client()

        # Delete source params: [[["source_id"]], [2]]
        # Note: Extra nesting compared to delete_notebook
        params = [[[source_id]], [2]]
        body = self._build_request_body(self.RPC_DELETE_SOURCE, params)
        url = self._build_url(self.RPC_DELETE_SOURCE)

        def _do_request():
            resp = client.post(url, content=body)
            resp.raise_for_status()
            return resp
        response = execute_with_retry(_do_request)

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_DELETE_SOURCE)

        # Response is typically [] on success
        return result is not None

    def get_notebook_sources_with_types(self, notebook_id: str) -> list[dict]:
        """Get all sources from a notebook with their type information."""
        result = self.get_notebook(notebook_id)

        sources = []
        # The notebook data is wrapped in an outer array
        if result and isinstance(result, list) and len(result) >= 1:
            notebook_data = result[0] if isinstance(result[0], list) else result
            # Sources are in notebook_data[1]
            sources_data = notebook_data[1] if len(notebook_data) > 1 else []

            if isinstance(sources_data, list):
                for src in sources_data:
                    if isinstance(src, list) and len(src) >= 3:
                        # Source structure: [[id], title, [metadata...], [null, 2]]
                        source_id = src[0][0] if src[0] and isinstance(src[0], list) else None
                        title = src[1] if len(src) > 1 else "Untitled"
                        metadata = src[2] if len(src) > 2 else []

                        source_type = None
                        drive_doc_id = None
                        if isinstance(metadata, list):
                            if len(metadata) > 4:
                                source_type = metadata[4]
                            # Drive doc info at metadata[0]
                            if len(metadata) > 0 and isinstance(metadata[0], list):
                                drive_doc_id = metadata[0][0] if metadata[0] else None

                        # Google Docs (type 1) and Slides/Sheets (type 2) are stored in Drive
                        # and can be synced if they have a drive_doc_id
                        can_sync = drive_doc_id is not None and source_type in (
                            self.SOURCE_TYPE_GOOGLE_DOCS,
                            self.SOURCE_TYPE_GOOGLE_OTHER,
                        )

                        # Extract URL if available (position 7)
                        url = None
                        if isinstance(metadata, list) and len(metadata) > 7:
                            url_info = metadata[7]
                            if isinstance(url_info, list) and len(url_info) > 0:
                                url = url_info[0]

                        # Extract processing status from src[3][1]
                        # 1=processing, 2=ready, 3=error, 5=preparing
                        status = self.SOURCE_STATUS_READY  # Default
                        if len(src) > 3 and isinstance(src[3], list) and len(src[3]) > 1:
                            status = src[3][1] if isinstance(src[3][1], int) else status

                        sources.append({
                            "id": source_id,
                            "title": title,
                            "source_type": source_type,
                            "source_type_name": constants.SOURCE_TYPES.get_name(source_type),
                            "url": url,
                            "drive_doc_id": drive_doc_id,
                            "can_sync": can_sync,
                            "status": status,
                        })

        return sources


    def add_url_source(
        self,
        notebook_id: str,
        url: str,
        wait: bool = False,
        wait_timeout: float = 120.0,
    ) -> dict | None:
        """Add a URL (website or YouTube) as a source to a notebook.
        
        Args:
            notebook_id: Target notebook ID
            url: URL to add
            wait: If True, block until source is ready
            wait_timeout: Seconds to wait if wait=True (default 120)
            
        Returns:
            Source dict with id and title, or None on failure
        """
        client = self._get_client()

        # URL position differs for YouTube vs regular websites:
        # - YouTube: position 7
        # - Regular websites: position 2
        is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()

        if is_youtube:
            # YouTube: [null, null, null, null, null, null, null, [url], null, null, 1]
            source_data = [None, None, None, None, None, None, None, [url], None, None, 1]
        else:
            # Regular website: [null, null, [url], null, null, null, null, null, null, null, 1]
            source_data = [None, None, [url], None, None, None, None, None, None, None, 1]

        params = [
            [source_data],
            notebook_id,
            [2],
            [1, None, None, None, None, None, None, None, None, None, [1]]
        ]
        body = self._build_request_body(self.RPC_ADD_SOURCE, params)
        source_path = f"/notebook/{notebook_id}"
        url_endpoint = self._build_url(self.RPC_ADD_SOURCE, source_path)

        try:
            def _do_request():
                resp = client.post(url_endpoint, content=body, timeout=SOURCE_ADD_TIMEOUT)
                resp.raise_for_status()
                return resp
            response = execute_with_retry(_do_request)
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": f"Operation timed out after {SOURCE_ADD_TIMEOUT}s but may have succeeded.",
            }

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_ADD_SOURCE)

        source_result = None
        if result and isinstance(result, list) and len(result) > 0:
            source_list = result[0] if result else []
            if source_list and len(source_list) > 0:
                source_data = source_list[0]
                source_id = source_data[0][0] if source_data[0] else None
                source_title = source_data[1] if len(source_data) > 1 else "Untitled"
                source_result = {"id": source_id, "title": source_title}
        
        if source_result and wait:
            return self.wait_for_source_ready(notebook_id, source_result["id"], wait_timeout)
        
        return source_result


    def add_text_source(
        self,
        notebook_id: str,
        text: str,
        title: str = "Pasted Text",
        wait: bool = False,
        wait_timeout: float = 120.0,
    ) -> dict | None:
        """Add pasted text as a source to a notebook.
        
        Args:
            notebook_id: Target notebook ID
            text: Text content to add
            title: Title for the source
            wait: If True, block until source is ready
            wait_timeout: Seconds to wait if wait=True (default 120)
        """
        client = self._get_client()

        # Text source params structure:
        source_data = [None, [title, text], None, 2, None, None, None, None, None, None, 1]
        params = [
            [source_data],
            notebook_id,
            [2],
            [1, None, None, None, None, None, None, None, None, None, [1]]
        ]
        body = self._build_request_body(self.RPC_ADD_SOURCE, params)
        source_path = f"/notebook/{notebook_id}"
        url_endpoint = self._build_url(self.RPC_ADD_SOURCE, source_path)

        try:
            def _do_request():
                resp = client.post(url_endpoint, content=body, timeout=SOURCE_ADD_TIMEOUT)
                resp.raise_for_status()
                return resp
            response = execute_with_retry(_do_request)
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": f"Operation timed out after {SOURCE_ADD_TIMEOUT}s.",
            }

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_ADD_SOURCE)

        source_result = None
        if result and isinstance(result, list) and len(result) > 0:
            source_list = result[0] if result else []
            if source_list and len(source_list) > 0:
                source_data = source_list[0]
                source_id = source_data[0][0] if source_data[0] else None
                source_title = source_data[1] if len(source_data) > 1 else title
                source_result = {"id": source_id, "title": source_title}
        
        if source_result and wait:
            return self.wait_for_source_ready(notebook_id, source_result["id"], wait_timeout)
        
        return source_result


    def add_drive_source(
        self,
        notebook_id: str,
        document_id: str,
        title: str,
        mime_type: str = "application/vnd.google-apps.document",
        wait: bool = False,
        wait_timeout: float = 120.0,
    ) -> dict | None:
        """Add a Google Drive document as a source to a notebook.
        
        Args:
            notebook_id: Target notebook ID
            document_id: Google Drive document ID
            title: Title for the source
            mime_type: MIME type of the Drive doc
            wait: If True, block until source is ready
            wait_timeout: Seconds to wait if wait=True (default 120)
        """
        client = self._get_client()

        source_data = [
            [document_id, mime_type, 1, title],
            None, None, None, None, None, None, None, None, None, 1
        ]
        params = [
            [source_data],
            notebook_id,
            [2],
            [1, None, None, None, None, None, None, None, None, None, [1]]
        ]
        body = self._build_request_body(self.RPC_ADD_SOURCE, params)
        source_path = f"/notebook/{notebook_id}"
        url_endpoint = self._build_url(self.RPC_ADD_SOURCE, source_path)

        try:
            def _do_request():
                resp = client.post(url_endpoint, content=body, timeout=SOURCE_ADD_TIMEOUT)
                resp.raise_for_status()
                return resp
            response = execute_with_retry(_do_request)
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": f"Operation timed out after {SOURCE_ADD_TIMEOUT}s.",
            }

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_ADD_SOURCE)

        source_result = None
        if result and isinstance(result, list) and len(result) > 0:
            source_list = result[0] if result else []
            if source_list and len(source_list) > 0:
                source_data = source_list[0]
                source_id = source_data[0][0] if source_data[0] else None
                source_title = source_data[1] if len(source_data) > 1 else title
                source_result = {"id": source_id, "title": source_title}
        
        if source_result and wait:
            return self.wait_for_source_ready(notebook_id, source_result["id"], wait_timeout)
        
        return source_result


    def _register_file_source(self, notebook_id: str, filename: str) -> str:
        """Register a file source intent and get SOURCE_ID.

        Step 1 of the resumable upload protocol.

        Args:
            notebook_id: The notebook to add the source to
            filename: The name of the file being uploaded

        Returns:
            The SOURCE_ID for the upload session

        Raises:
            FileUploadError: If registration fails
        """
        client = self._get_client()

        # Params: [[filename]], notebook_id, [2], [options]
        params = [
            [[filename]],
            notebook_id,
            [2],
            [1, None, None, None, None, None, None, None, None, None, [1]],
        ]

        body = self._build_request_body(self.RPC_ADD_SOURCE_FILE, params)
        source_path = f"/notebook/{notebook_id}"
        url = self._build_url(self.RPC_ADD_SOURCE_FILE, source_path)

        def _do_request():
            resp = client.post(url, content=body, timeout=60.0)
            resp.raise_for_status()
            return resp
        response = execute_with_retry(_do_request)

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_ADD_SOURCE_FILE)

        # Extract SOURCE_ID from nested response
        def extract_id(data):
            if isinstance(data, str):
                return data
            if isinstance(data, list) and len(data) > 0:
                return extract_id(data[0])
            return None

        if result and isinstance(result, list):
            source_id = extract_id(result)
            if source_id:
                return source_id

        raise FileUploadError(filename, "Failed to get SOURCE_ID from registration response")

    def _start_resumable_upload(
        self,
        notebook_id: str,
        filename: str,
        file_size: int,
        source_id: str,
    ) -> str:
        """Start a resumable upload session and get the upload URL.

        Step 2 of the resumable upload protocol.

        Args:
            notebook_id: The notebook ID
            filename: The filename
            file_size: Size of file in bytes
            source_id: The SOURCE_ID from step 1

        Returns:
            The upload URL for step 3

        Raises:
            FileUploadError: If starting the upload session fails
        """
        import json

        url = f"{self.UPLOAD_URL}?authuser=0"
        cookies = self._get_httpx_cookies()

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://notebooklm.google.com",
            "Referer": "https://notebooklm.google.com/",
            "x-goog-authuser": "0",
            "x-goog-upload-command": "start",
            "x-goog-upload-header-content-length": str(file_size),
            "x-goog-upload-protocol": "resumable",
        }

        body = json.dumps({
            "PROJECT_ID": notebook_id,
            "SOURCE_NAME": filename,
            "SOURCE_ID": source_id,
        })

        with httpx.Client(timeout=60.0, cookies=cookies) as client:
            def _do_request():
                resp = client.post(url, headers=headers, content=body)
                resp.raise_for_status()
                return resp
            response = execute_with_retry(_do_request)

            upload_url = response.headers.get("x-goog-upload-url")
            if not upload_url:
                raise FileUploadError(filename, "Failed to get upload URL from response headers")

            return upload_url

    def _upload_file_streaming(self, upload_url: str, file_path: Path) -> None:
        """Stream upload file content to the resumable upload URL.

        Step 3 of the resumable upload protocol. Uses streaming to
        avoid loading the entire file into memory.

        Args:
            upload_url: The upload URL from step 2
            file_path: Path to the file to upload

        Raises:
            FileUploadError: If the upload fails
        """
        cookies = self._get_httpx_cookies()

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Origin": "https://notebooklm.google.com",
            "Referer": "https://notebooklm.google.com/",
            "x-goog-authuser": "0",
            "x-goog-upload-command": "upload, finalize",
            "x-goog-upload-offset": "0",
        }

        # Generator for streaming file content
        def file_stream():
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):  # 64KB chunks
                    yield chunk

        with httpx.Client(timeout=300.0, cookies=cookies) as client:
            def _do_upload():
                resp = client.post(upload_url, headers=headers, content=file_stream())
                resp.raise_for_status()
                return resp
            execute_with_retry(_do_upload)

    def add_file(
        self,
        notebook_id: str,
        file_path: str | Path,
        wait: bool = False,
        wait_timeout: float = 120.0,
    ) -> dict:
        """Add a local file as a source using resumable upload.

        Uses Google's resumable upload protocol:
        1. Register source intent with RPC → get SOURCE_ID
        2. Start upload session with SOURCE_ID → get upload URL
        3. Stream upload file content (memory-efficient for large files)

        Supported file types: PDF, TXT, MD, DOCX, CSV, MP3, MP4, JPG, PNG

        Args:
            notebook_id: The notebook ID to add the source to
            file_path: Path to the local file to upload
            wait: If True, poll until source is processed (default: False)
            wait_timeout: Max seconds to wait if wait=True (default: 120)

        Returns:
            dict with 'id' and 'title' of the created source

        Raises:
            FileValidationError: If file doesn't exist or is invalid
            FileUploadError: If upload fails
        """
        file_path = Path(file_path)

        # Validate file
        if not file_path.exists():
            raise FileValidationError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise FileValidationError(f"Not a regular file: {file_path}")

        filename = file_path.name
        file_size = file_path.stat().st_size

        if file_size == 0:
            raise FileValidationError(f"File is empty: {file_path}")

        # Validate file type
        supported_extensions = {'.pdf', '.txt', '.md', '.docx', '.csv', '.mp3', '.mp4', '.jpg', '.jpeg', '.png'}
        file_extension = file_path.suffix.lower()
        if file_extension not in supported_extensions:
            raise FileValidationError(
                f"Unsupported file type: {file_extension}\n"
                f"Supported types: {', '.join(sorted(supported_extensions))}"
            )

        # Step 1: Register source intent → get SOURCE_ID
        source_id = self._register_file_source(notebook_id, filename)

        # Step 2: Start resumable upload → get upload URL
        upload_url = self._start_resumable_upload(notebook_id, filename, file_size, source_id)

        # Step 3: Stream upload file content
        self._upload_file_streaming(upload_url, file_path)

        result = {"id": source_id, "title": filename}

        if wait:
            return self.wait_for_source_ready(notebook_id, source_id, wait_timeout)

        return result


    def get_source_guide(self, source_id: str) -> dict[str, Any]:
        """Get AI-generated summary and keywords for a source."""
        result = self._call_rpc(self.RPC_GET_SOURCE_GUIDE, [[[[source_id]]]], "/")
        summary = ""
        keywords = []

        if result and isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], list):
                if len(result[0]) > 0 and isinstance(result[0][0], list):
                    inner = result[0][0]

                    if len(inner) > 1 and isinstance(inner[1], list) and len(inner[1]) > 0:
                        summary = inner[1][0]

                    if len(inner) > 2 and isinstance(inner[2], list) and len(inner[2]) > 0:
                        keywords = inner[2][0] if isinstance(inner[2][0], list) else []

        return {
            "summary": summary,
            "keywords": keywords,
        }

    def get_source_fulltext(self, source_id: str) -> dict[str, Any]:
        """Get the full text content of a source.

        Returns the raw text content that was indexed from the source,
        along with metadata like title and source type.

        Args:
            source_id: The source UUID

        Returns:
            Dict with content, title, source_type, and char_count
        """
        # The hizoJc RPC returns source details including full text
        params = [[source_id], [2], [2]]
        result = self._call_rpc(self.RPC_GET_SOURCE, params, "/")

        content = ""
        title = ""
        source_type = ""
        url = None

        if result and isinstance(result, list):
            # Response structure:
            # result[0] = [[source_id], title, metadata, ...]
            # result[1] = null
            # result[2] = null
            # result[3] = [[content_blocks]]
            #
            # Each content block: [start_pos, end_pos, content_data, ...]

            # Extract from result[0] which contains source metadata
            if len(result) > 0 and isinstance(result[0], list):
                source_meta = result[0]

                # Title is at position 1
                if len(source_meta) > 1 and isinstance(source_meta[1], str):
                    title = source_meta[1]

                # Metadata is at position 2
                if len(source_meta) > 2 and isinstance(source_meta[2], list):
                    metadata = source_meta[2]
                    # Source type code is at position 4
                    if len(metadata) > 4:
                        type_code = metadata[4]
                        source_type = constants.SOURCE_TYPES.get_name(type_code)

                    # URL might be at position 7 for web sources
                    if len(metadata) > 7 and isinstance(metadata[7], list):
                        url_info = metadata[7]
                        if len(url_info) > 0 and isinstance(url_info[0], str):
                            url = url_info[0]

            # Extract content from result[3][0] - array of content blocks
            if len(result) > 3 and isinstance(result[3], list):
                content_wrapper = result[3]
                if len(content_wrapper) > 0 and isinstance(content_wrapper[0], list):
                    content_blocks = content_wrapper[0]
                    # Collect all text from content blocks
                    text_parts = []
                    for block in content_blocks:
                        if isinstance(block, list):
                            # Each block is [start, end, content_data, ...]
                            # Extract all text strings recursively
                            texts = self._extract_all_text(block)
                            text_parts.extend(texts)
                    content = "\n\n".join(text_parts)

        return {
            "content": content,
            "title": title,
            "source_type": source_type,
            "url": url,
            "char_count": len(content),
        }

    def _extract_all_text(self, data: list) -> list[str]:
        """Recursively extract all text strings from nested arrays."""
        texts = []
        for item in data:
            if isinstance(item, str) and len(item) > 0:
                texts.append(item)
            elif isinstance(item, list):
                texts.extend(self._extract_all_text(item))
        return texts
