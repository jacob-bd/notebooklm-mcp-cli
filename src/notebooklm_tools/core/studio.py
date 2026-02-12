#!/usr/bin/env python3
"""StudioMixin for NotebookLM client - studio content creation and status."""

from typing import Callable

from . import constants
from .base import BaseClient
from .utils import parse_timestamp


class StudioMixin(BaseClient):
    """Mixin providing studio content creation and status operations.

    This mixin handles all studio artifact operations:
    - Audio overview creation (podcasts)
    - Video overview creation
    - Report generation (briefing docs, study guides, blog posts)
    - Flashcards and quiz generation
    - Infographic creation
    - Slide deck creation
    - Data table creation
    - Mind map generation and management
    - Status polling and artifact deletion
    """

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_all_source_ids(self, notebook_id: str) -> list[str]:
        """Get all source IDs from a notebook.

        Uses get_notebook_sources_with_types() for structured, reliable access.

        Args:
            notebook_id: The notebook UUID

        Returns:
            List of source UUIDs, or empty list if none found
        """
        try:
            sources = self.get_notebook_sources_with_types(notebook_id)
            return [s["id"] for s in sources if s.get("id")]
        except Exception:
            # Return empty list on error - caller methods will handle gracefully
            return []

    # =========================================================================
    # Studio Operations
    # =========================================================================

    def create_audio_overview(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format_code: int = 1,  # AUDIO_FORMAT_DEEP_DIVE
        length_code: int = 2,  # AUDIO_LENGTH_DEFAULT
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create an Audio Overview (podcast) for a notebook."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Build source IDs in the simpler format: [[id1], [id2], ...]
        sources_simple = [[sid] for sid in source_ids]

        audio_options = [
            None,
            [
                focus_prompt,
                length_code,
                None,
                sources_simple,
                language,
                None,
                format_code
            ]
        ]

        params = [
            [2],
            notebook_id,
            [
                None, None,
                self.STUDIO_TYPE_AUDIO,
                sources_nested,
                None, None,
                audio_options
            ]
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "audio",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "format": constants.AUDIO_FORMATS.get_name(format_code),
                "length": constants.AUDIO_LENGTHS.get_name(length_code),
                "language": language,
            }

        return None

    def create_video_overview(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format_code: int = 1,  # VIDEO_FORMAT_EXPLAINER
        visual_style_code: int = 1,  # VIDEO_STYLE_AUTO_SELECT
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create a Video Overview for a notebook."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Build source IDs in the simpler format: [[id1], [id2], ...]
        sources_simple = [[sid] for sid in source_ids]

        video_options = [
            None, None,
            [
                sources_simple,
                language,
                focus_prompt,
                None,
                format_code,
                visual_style_code
            ]
        ]

        params = [
            [2],
            notebook_id,
            [
                None, None,
                self.STUDIO_TYPE_VIDEO,
                sources_nested,
                None, None, None, None,
                video_options
            ]
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "video",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "format": constants.VIDEO_FORMATS.get_name(format_code),
                "visual_style": constants.VIDEO_STYLES.get_name(visual_style_code),
                "language": language,
            }

        return None

    def poll_studio_status(self, notebook_id: str) -> list[dict]:
        """Poll for studio content (audio/video overviews) status."""
        client = self._get_client()

        # Poll params: [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        params = [[2], notebook_id, 'NOT artifact.status = "ARTIFACT_STATUS_SUGGESTED"']
        body = self._build_request_body(self.RPC_POLL_STUDIO, params)
        url = self._build_url(self.RPC_POLL_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_POLL_STUDIO)

        artifacts = []
        if result and isinstance(result, list) and len(result) > 0:
            # Response is an array of artifacts, possibly wrapped
            artifact_list = result[0] if isinstance(result[0], list) else result

            for artifact_data in artifact_list:
                if not isinstance(artifact_data, list) or len(artifact_data) < 5:
                    continue

                artifact_id = artifact_data[0]
                title = artifact_data[1] if len(artifact_data) > 1 else ""
                type_code = artifact_data[2] if len(artifact_data) > 2 else None
                status_code = artifact_data[4] if len(artifact_data) > 4 else None

                audio_url = None
                video_url = None
                duration_seconds = None

                # Audio artifacts have URLs at position 6
                if type_code == self.STUDIO_TYPE_AUDIO and len(artifact_data) > 6:
                    audio_options = artifact_data[6]
                    if isinstance(audio_options, list) and len(audio_options) > 3:
                        audio_url = audio_options[3] if isinstance(audio_options[3], str) else None
                        # Duration is often at position 9
                        if len(audio_options) > 9 and isinstance(audio_options[9], list):
                            duration_seconds = audio_options[9][0] if audio_options[9] else None

                # Video artifacts have URLs at position 8
                if type_code == self.STUDIO_TYPE_VIDEO and len(artifact_data) > 8:
                    video_options = artifact_data[8]
                    if isinstance(video_options, list) and len(video_options) > 3:
                        video_url = video_options[3] if isinstance(video_options[3], str) else None

                # Infographic artifacts have image URL at position 14
                infographic_url = None
                if type_code == self.STUDIO_TYPE_INFOGRAPHIC and len(artifact_data) > 14:
                    infographic_options = artifact_data[14]
                    if isinstance(infographic_options, list) and len(infographic_options) > 2:
                        # URL is at [2][0][1][0] - image_data[0][1][0]
                        image_data = infographic_options[2]
                        if isinstance(image_data, list) and len(image_data) > 0:
                            first_image = image_data[0]
                            if isinstance(first_image, list) and len(first_image) > 1:
                                image_details = first_image[1]
                                if isinstance(image_details, list) and len(image_details) > 0:
                                    url = image_details[0]
                                    if isinstance(url, str) and url.startswith("http"):
                                        infographic_url = url

                # Slide deck artifacts have download URL at position 16
                slide_deck_url = None
                if type_code == self.STUDIO_TYPE_SLIDE_DECK and len(artifact_data) > 16:
                    slide_deck_options = artifact_data[16]
                    if isinstance(slide_deck_options, list) and len(slide_deck_options) > 0:
                        # URL is typically at position 0 in the options
                        if isinstance(slide_deck_options[0], str) and slide_deck_options[0].startswith("http"):
                            slide_deck_url = slide_deck_options[0]
                        # Or may be nested deeper
                        elif len(slide_deck_options) > 3 and isinstance(slide_deck_options[3], str):
                            slide_deck_url = slide_deck_options[3]

                # Report artifacts have content at position 7
                report_content = None
                if type_code == self.STUDIO_TYPE_REPORT and len(artifact_data) > 7:
                    report_options = artifact_data[7]
                    if isinstance(report_options, list) and len(report_options) > 1:
                        # Content is nested in the options
                        content_data = report_options[1] if isinstance(report_options[1], list) else None
                        if content_data and len(content_data) > 0:
                            # Report content is typically markdown text
                            report_content = content_data[0] if isinstance(content_data[0], str) else None

                # Flashcard/Quiz artifacts have cards data at position 9
                # Quiz and Flashcards share type code 4, distinguished by options[1][0]:
                #   - Flashcards: options[1][0] == 1
                #   - Quiz: options[1][0] == 2
                flashcard_count = None
                is_quiz = False
                if type_code == self.STUDIO_TYPE_FLASHCARDS and len(artifact_data) > 9:
                    flashcard_options = artifact_data[9]
                    if isinstance(flashcard_options, list) and len(flashcard_options) > 1:
                        inner_options = flashcard_options[1]
                        if isinstance(inner_options, list) and len(inner_options) > 0:
                            # Check format code: 1=flashcards, 2=quiz
                            format_code = inner_options[0]
                            if format_code == 2:
                                is_quiz = True
                        # Count cards in the data
                        cards_data = flashcard_options[1] if isinstance(flashcard_options[1], list) else None
                        if cards_data:
                            flashcard_count = len(cards_data) if isinstance(cards_data, list) else None

                # Extract created_at timestamp
                # Position varies by type but often at position 10, 15, or similar
                created_at = None
                # Try common timestamp positions
                for ts_pos in [10, 15, 17]:
                    if len(artifact_data) > ts_pos:
                        ts_candidate = artifact_data[ts_pos]
                        if isinstance(ts_candidate, list) and len(ts_candidate) >= 2:
                            # Check if it looks like a timestamp [seconds, nanos]
                            if isinstance(ts_candidate[0], (int, float)) and ts_candidate[0] > 1700000000:
                                created_at = parse_timestamp(ts_candidate)
                                break

                # Map type codes to type names
                type_map = {
                    self.STUDIO_TYPE_AUDIO: "audio",
                    self.STUDIO_TYPE_REPORT: "report",
                    self.STUDIO_TYPE_VIDEO: "video",
                    self.STUDIO_TYPE_FLASHCARDS: "flashcards",  # Quiz also uses type 4, but detected via is_quiz
                    self.STUDIO_TYPE_INFOGRAPHIC: "infographic",
                    self.STUDIO_TYPE_SLIDE_DECK: "slide_deck",
                    self.STUDIO_TYPE_DATA_TABLE: "data_table",
                }
                artifact_type = "quiz" if is_quiz else type_map.get(type_code, "unknown")
                status_map = {
                    1: "in_progress",
                    3: "completed",
                    4: "failed",
                }
                status = status_map.get(status_code, "unknown")

                # Extract custom_instructions (focus prompt) if present
                # Custom prompt is stored at artifact_data[STUDIO_ARTIFACT_FOCUS_INDEX][1][0] for artifacts that have one
                custom_instructions = None
                
                if len(artifact_data) > constants.STUDIO_ARTIFACT_FOCUS_INDEX:
                    options_data = artifact_data[constants.STUDIO_ARTIFACT_FOCUS_INDEX]
                    if isinstance(options_data, list) and len(options_data) > 1:
                        inner = options_data[1]
                        if isinstance(inner, list) and len(inner) > 0:
                            if isinstance(inner[0], str) and inner[0]:
                                custom_instructions = inner[0]

                artifacts.append({
                    "artifact_id": artifact_id,
                    "title": title,
                    "type": artifact_type,
                    "status": status,
                    "created_at": created_at,
                    "custom_instructions": custom_instructions,
                    "audio_url": audio_url,
                    "video_url": video_url,
                    "infographic_url": infographic_url,
                    "slide_deck_url": slide_deck_url,
                    "report_content": report_content,
                    "flashcard_count": flashcard_count,
                    "duration_seconds": duration_seconds,
                })

        return artifacts

    def get_studio_status(self, notebook_id: str) -> list[dict]:
        """Alias for poll_studio_status (used by CLI)."""
        return self.poll_studio_status(notebook_id)

    def delete_studio_artifact(self, artifact_id: str, notebook_id: str | None = None) -> bool:
        """Delete a studio artifact (Audio, Video, or Mind Map).

        WARNING: This action is IRREVERSIBLE. The artifact will be permanently deleted.

        Args:
            artifact_id: The artifact UUID to delete
            notebook_id: Optional notebook ID. Required for deleting Mind Maps.

        Returns:
            True on success, False on failure
        """
        # 1. Try standard deletion (Audio, Video, etc.)
        try:
            params = [[2], artifact_id]
            result = self._call_rpc(self.RPC_DELETE_STUDIO, params)
            if result is not None:
                return True
        except Exception:
            # Continue to fallback if standard delete fails
            pass

        # 2. Fallback: Try Mind Map deletion if we have a notebook ID
        # Mind maps require a different RPC (AH0mwd) and payload structure
        if notebook_id:
            return self.delete_mind_map(notebook_id, artifact_id)

        return False

    def delete_mind_map(self, notebook_id: str, mind_map_id: str) -> bool:
        """Delete a Mind Map artifact using the observed two-step RPC sequence.

        Args:
            notebook_id: The notebook UUID.
            mind_map_id: The Mind Map artifact UUID.

        Returns:
            True on success
        """
        # 1. We need the artifact-specific timestamp from LIST_MIND_MAPS
        params = [notebook_id]
        list_result = self._call_rpc(
            self.RPC_LIST_MIND_MAPS, params, f"/notebook/{notebook_id}"
        )

        timestamp = None
        if list_result and isinstance(list_result, list) and len(list_result) > 0:
            mm_list = list_result[0] if isinstance(list_result[0], list) else []
            for mm_entry in mm_list:
                if isinstance(mm_entry, list) and mm_entry[0] == mind_map_id:
                    # Based on debug output: item[1][2][2] contains [seconds, micros]
                    try:
                        timestamp = mm_entry[1][2][2]
                    except (IndexError, TypeError):
                        pass
                    break

        # 2. Step 1: UUID-based deletion (AH0mwd)
        params_v2 = [notebook_id, None, [mind_map_id], [2]]
        self._call_rpc(self.RPC_DELETE_MIND_MAP, params_v2, f"/notebook/{notebook_id}")

        # 3. Step 2: Timestamp-based sync/deletion (cFji9)
        # This is required to fully remove it from the list and avoid "ghosts"
        if timestamp:
            params_v1 = [notebook_id, None, timestamp, [2]]
            self._call_rpc(self.RPC_LIST_MIND_MAPS, params_v1, f"/notebook/{notebook_id}")

        return True

    def rename_studio_artifact(self, artifact_id: str, new_title: str) -> bool:
        """Rename a studio artifact (Audio, Video, Report, etc.).

        Args:
            artifact_id: The artifact UUID to rename
            new_title: The new title for the artifact

        Returns:
            True on success, False on failure
        """
        # Payload structure discovered via browser network intercept:
        # [[ "<artifact_id>", "<new_title>" ], [["title"]]]
        params = [[artifact_id, new_title], [["title"]]]
        
        try:
            result = self._call_rpc(self.RPC_RENAME_ARTIFACT, params)
            return result is not None
        except Exception:
            return False


    def create_infographic(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        orientation_code: int = 1,  # INFOGRAPHIC_ORIENTATION_LANDSCAPE
        detail_level_code: int = 2,  # INFOGRAPHIC_DETAIL_STANDARD
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create an Infographic from notebook sources."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Options at position 14: [[focus_prompt, language, null, orientation, detail_level]]
        # Captured RPC structure was [[null, "en", null, 1, 2]]
        infographic_options = [[focus_prompt or None, language, None, orientation_code, detail_level_code]]

        content = [
            None, None,
            self.STUDIO_TYPE_INFOGRAPHIC,
            sources_nested,
            None, None, None, None, None, None, None, None, None, None,  # 10 nulls (positions 4-13)
            infographic_options  # position 14
        ]

        params = [
            [2],
            notebook_id,
            content
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "infographic",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "orientation": constants.INFOGRAPHIC_ORIENTATIONS.get_name(orientation_code),
                "detail_level": constants.INFOGRAPHIC_DETAILS.get_name(detail_level_code),
                "language": language,
            }

        return None

    def create_slide_deck(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        format_code: int = 1,  # SLIDE_DECK_FORMAT_DETAILED
        length_code: int = 3,  # SLIDE_DECK_LENGTH_DEFAULT
        language: str = "en",
        focus_prompt: str = "",
    ) -> dict | None:
        """Create a Slide Deck from notebook sources."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Options at position 16: [[focus_prompt, language, format, length]]
        slide_deck_options = [[focus_prompt or None, language, format_code, length_code]]

        content = [
            None, None,
            self.STUDIO_TYPE_SLIDE_DECK,
            sources_nested,
            None, None, None, None, None, None, None, None, None, None, None, None,  # 12 nulls (positions 4-15)
            slide_deck_options  # position 16
        ]

        params = [
            [2],
            notebook_id,
            content
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "slide_deck",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "format": constants.SLIDE_DECK_FORMATS.get_name(format_code),
                "length": constants.SLIDE_DECK_LENGTHS.get_name(length_code),
                "language": language,
            }

        return None

    def create_report(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        report_format: str = "Briefing Doc",
        custom_prompt: str = "",
        language: str = "en",
    ) -> dict | None:
        """Create a Report from notebook sources."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Build source IDs in the simpler format: [[id1], [id2], ...]
        sources_simple = [[sid] for sid in source_ids]

        # Map report format to title, description, and prompt
        format_configs = {
            "Briefing Doc": {
                "title": "Briefing Doc",
                "description": "Key insights and important quotes",
                "prompt": (
                    "Create a comprehensive briefing document that includes an "
                    "Executive Summary, detailed analysis of key themes, important "
                    "quotes with context, and actionable insights."
                ),
            },
            "Study Guide": {
                "title": "Study Guide",
                "description": "Short-answer quiz, essay questions, glossary",
                "prompt": (
                    "Create a comprehensive study guide that includes key concepts, "
                    "short-answer practice questions, essay prompts for deeper "
                    "exploration, and a glossary of important terms."
                ),
            },
            "Blog Post": {
                "title": "Blog Post",
                "description": "Insightful takeaways in readable article format",
                "prompt": (
                    "Write an engaging blog post that presents the key insights "
                    "in an accessible, reader-friendly format. Include an attention-"
                    "grabbing introduction, well-organized sections, and a compelling "
                    "conclusion with takeaways."
                ),
            },
            "Create Your Own": {
                "title": "Custom Report",
                "description": "Custom format",
                "prompt": custom_prompt or "Create a report based on the provided sources.",
            },
        }

        if report_format not in format_configs:
            raise ValueError(
                f"Invalid report_format: {report_format}. "
                f"Must be one of: {list(format_configs.keys())}"
            )

        config = format_configs[report_format]

        # Options at position 7: [null, [title, desc, null, sources, lang, prompt, null, True]]
        report_options = [
            None,
            [
                config["title"],
                config["description"],
                None,
                sources_simple,
                language,
                config["prompt"],
                None,
                True
            ]
        ]

        content = [
            None, None,
            self.STUDIO_TYPE_REPORT,
            sources_nested,
            None, None, None,
            report_options
        ]

        params = [
            [2],
            notebook_id,
            content
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "report",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "format": report_format,
                "language": language,
            }

        return None

    def create_flashcards(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        difficulty_code: int = 2,  # FLASHCARD_DIFFICULTY_MEDIUM
    ) -> dict | None:
        """Create Flashcards from notebook sources."""
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        # Card count code (default = 2)
        count_code = constants.FLASHCARD_COUNT_DEFAULT

        # Options at position 9: [null, [1, null*5, [difficulty, card_count]]]
        flashcard_options = [
            None,
            [
                1,  # Unknown (possibly default count base)
                None, None, None, None, None,
                [difficulty_code, count_code]
            ]
        ]

        content = [
            None, None,
            self.STUDIO_TYPE_FLASHCARDS,
            sources_nested,
            None, None, None, None, None,  # 5 nulls (positions 4-8)
            flashcard_options  # position 9
        ]

        params = [
            [2],
            notebook_id,
            content
        ]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "flashcards",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "difficulty": constants.FLASHCARD_DIFFICULTIES.get_name(difficulty_code),
            }

        return None

    def create_quiz(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        question_count: int = 2,
        difficulty: int = 2,
    ) -> dict | None:
        """Create Quiz from notebook sources.

        Args:
            notebook_id: Notebook UUID
            source_ids: List of source UUIDs (defaults to all sources)
            question_count: Number of questions (default: 2)
            difficulty: Difficulty level (default: 2)
        """
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        sources_nested = [[[sid]] for sid in source_ids]

        # Quiz options at position 9: [null, [2, null*6, [question_count, difficulty]]]
        quiz_options = [
            None,
            [
                2,  # Format/variant code
                None, None, None, None, None, None,
                [question_count, difficulty]
            ]
        ]

        content = [
            None, None,
            self.STUDIO_TYPE_FLASHCARDS,  # Type 4 (shared with flashcards)
            sources_nested,
            None, None, None, None, None,
            quiz_options  # position 9
        ]

        params = [[2], notebook_id, content]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "quiz",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "question_count": question_count,
                "difficulty": constants.FLASHCARD_DIFFICULTIES.get_name(difficulty),
            }

        return None

    def create_data_table(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
        description: str = "",
        language: str = "en",
    ) -> dict | None:
        """Create Data Table from notebook sources.

        Args:
            notebook_id: Notebook UUID
            source_ids: List of source UUIDs (defaults to all sources)
            description: Description of the data table to create
            language: Language code (default: "en")
        """
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        sources_nested = [[[sid]] for sid in source_ids]

        # Data Table options at position 18: [null, [description, language]]
        datatable_options = [None, [description, language]]

        content = [
            None, None,
            self.STUDIO_TYPE_DATA_TABLE,  # Type 9
            sources_nested,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None,  # 14 nulls (positions 4-17)
            datatable_options  # position 18
        ]

        params = [[2], notebook_id, content]

        body = self._build_request_body(self.RPC_CREATE_STUDIO, params)
        url = self._build_url(self.RPC_CREATE_STUDIO, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_CREATE_STUDIO)

        if result and isinstance(result, list) and len(result) > 0:
            artifact_data = result[0]
            artifact_id = artifact_data[0] if isinstance(artifact_data, list) and len(artifact_data) > 0 else None
            status_code = artifact_data[4] if isinstance(artifact_data, list) and len(artifact_data) > 4 else None

            return {
                "artifact_id": artifact_id,
                "notebook_id": notebook_id,
                "type": "data_table",
                "status": "in_progress" if status_code == 1 else "completed" if status_code == 3 else "unknown",
                "description": description,
            }

        return None

    def generate_mind_map(
        self,
        notebook_id: str,
        source_ids: list[str] | None = None,
    ) -> dict | None:
        """Generate a Mind Map JSON from sources.

        This is step 1 of 2 for creating a mind map. After generation,
        use save_mind_map() to save it to a notebook.

        BREAKING CHANGE (v0.2.3+):
            The signature changed from generate_mind_map(source_ids) to
            generate_mind_map(notebook_id, source_ids=None).

            Old usage: generate_mind_map(["source1", "source2"])
            New usage: generate_mind_map("notebook_id", ["source1", "source2"])

            If source_ids is None, all sources in the notebook will be used.

        Args:
            notebook_id: Notebook UUID (used to get sources if source_ids not provided)
            source_ids: List of source UUIDs to include (defaults to all sources)

        Returns:
            Dict with mind_map_json and generation_id, or None on failure

        Raises:
            ValueError: If no sources found in notebook
        """
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the nested format: [[[id1]], [[id2]], ...]
        sources_nested = [[[sid]] for sid in source_ids]

        params = [
            sources_nested,
            None, None, None, None,
            ["interactive_mindmap", [["[CONTEXT]", ""]], ""],
            None,
            [2, None, [1]]
        ]

        body = self._build_request_body(self.RPC_GENERATE_MIND_MAP, params)
        url = self._build_url(self.RPC_GENERATE_MIND_MAP)

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_GENERATE_MIND_MAP)

        if result and isinstance(result, list) and len(result) > 0:
            # Response is nested: [[json_string, null, [gen_ids]]]
            # So result[0] is [json_string, null, [gen_ids]]
            inner = result[0] if isinstance(result[0], list) else result

            mind_map_json = inner[0] if isinstance(inner[0], str) else None
            generation_info = inner[2] if len(inner) > 2 else None

            generation_id = None
            if isinstance(generation_info, list) and len(generation_info) > 0:
                generation_id = generation_info[0]

            return {
                "mind_map_json": mind_map_json,
                "generation_id": generation_id,
                "source_ids": source_ids,
            }

        return None

    def save_mind_map(
        self,
        notebook_id: str,
        mind_map_json: str,
        source_ids: list[str] | None = None,
        title: str = "Mind Map",
    ) -> dict | None:
        """Save a generated Mind Map to a notebook.

        This is step 2 of 2 for creating a mind map. First use
        generate_mind_map() to create the JSON structure.

        Args:
            notebook_id: The notebook UUID
            mind_map_json: The JSON string from generate_mind_map()
            source_ids: List of source UUIDs used to generate the map (defaults to all sources)
            title: Display title for the mind map

        Returns:
            Dict with mind_map_id and saved info, or None on failure
        """
        client = self._get_client()

        # Default to all sources if not specified
        if source_ids is None:
            source_ids = self._get_all_source_ids(notebook_id)

        if not source_ids:
            raise ValueError(f"No sources found in notebook {notebook_id}. Add sources before creating studio content.")

        # Build source IDs in the simpler format: [[id1], [id2], ...]
        sources_simple = [[sid] for sid in source_ids]

        metadata = [2, None, None, 5, sources_simple]

        params = [
            notebook_id,
            mind_map_json,
            metadata,
            None,
            title
        ]

        body = self._build_request_body(self.RPC_SAVE_MIND_MAP, params)
        url = self._build_url(self.RPC_SAVE_MIND_MAP, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_SAVE_MIND_MAP)

        if result and isinstance(result, list) and len(result) > 0:
            # Response is nested: [[mind_map_id, json, metadata, null, title]]
            inner = result[0] if isinstance(result[0], list) else result

            mind_map_id = inner[0] if len(inner) > 0 else None
            saved_json = inner[1] if len(inner) > 1 else None
            saved_title = inner[4] if len(inner) > 4 else title

            return {
                "mind_map_id": mind_map_id,
                "notebook_id": notebook_id,
                "title": saved_title,
                "mind_map_json": saved_json,
            }

        return None

    def list_mind_maps(self, notebook_id: str) -> list[dict]:
        """List all Mind Maps in a notebook."""
        client = self._get_client()

        params = [notebook_id]

        body = self._build_request_body(self.RPC_LIST_MIND_MAPS, params)
        url = self._build_url(self.RPC_LIST_MIND_MAPS, f"/notebook/{notebook_id}")

        response = client.post(url, content=body)
        response.raise_for_status()

        parsed = self._parse_response(response.text)
        result = self._extract_rpc_result(parsed, self.RPC_LIST_MIND_MAPS)

        mind_maps = []
        if result and isinstance(result, list) and len(result) > 0:
            mind_map_list = result[0] if isinstance(result[0], list) else []

            for mind_map_data in mind_map_list:
                # Skip invalid or tombstone entries (deleted entries have details=None)
                # Tombstone format: [uuid, null, 2]
                if not isinstance(mind_map_data, list) or len(mind_map_data) < 2:
                    continue
                
                details = mind_map_data[1]
                if details is None:
                    # This is a tombstone/deleted entry, skip it
                    continue

                mind_map_id = mind_map_data[0]

                if isinstance(details, list) and len(details) >= 5:
                    # Details: [id, json, metadata, null, title]
                    mind_map_json = details[1] if len(details) > 1 else None
                    title = details[4] if len(details) > 4 else "Mind Map"
                    metadata = details[2] if len(details) > 2 else []

                    created_at = None
                    if isinstance(metadata, list) and len(metadata) > 2:
                        ts = metadata[2]
                        created_at = parse_timestamp(ts)

                    mind_maps.append({
                        "mind_map_id": mind_map_id,
                        "title": title,
                        "mind_map_json": mind_map_json,
                        "created_at": created_at,
                    })

        return mind_maps
