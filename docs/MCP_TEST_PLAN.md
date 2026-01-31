# NotebookLM MCP - Comprehensive Test Plan

**Purpose:** Verify all **29 consolidated MCP tools** work correctly.

**Version:** 2.2 (Updated 2026-01-31 - corrected tool count)

**Changes from v2.1:**
- Corrected tool count: 29 tools (notes consolidated + server_info added)

**Changes from v1:**
- Tools consolidated: 45+ → 29 (-36%)
- `source_add(type=...)` replaces 4 source tools
- `studio_create(type=...)` replaces 9 creation tools
- `download_artifact(type=...)` replaces 9 download tools

**Prerequisites:**
- MCP server installed: `uv cache clean && uv tool install --force .`
- Valid authentication cookies saved
- **Restart IDE MCP server** after installation

---

## Automated Testing with AI Tools

**Simply ask your AI assistant to:**
```
Run the automated tests from docs/MCP_TEST_PLAN.md. For the Drive sync test,
pause before checking freshness, ask me to make a change to the doc, then
verify both staleness detection and sync functionality work correctly.
```

### How Automation Works

1. **Execute tests sequentially** - Run through each test group automatically
2. **Track progress** - Use a todo list to show what's being tested
3. **Pause for user input** - Stop at Drive sync test to ask you to modify a document
4. **Report results** - Provide a comprehensive summary of all tests

---

## Test Group 1: Authentication & Basic Operations

### Test 1.1 - Refresh Auth
**Tool:** `refresh_auth`

**Prompt:**
```
Refresh authentication tokens for NotebookLM.
```

**Expected:** Success message with auth status.

---

### Test 1.2 - Save Auth Tokens (Fallback)
**Tool:** `save_auth_tokens`

**Prompt:**
```
I have cookies from Chrome DevTools. Save them using save_auth_tokens.
[Note: Use actual cookies from your browser session]
```

**Expected:** Success message with cache path.

---

### Test 1.3 - List Notebooks
**Tool:** `notebook_list`

**Prompt:**
```
List all my NotebookLM notebooks.
```

**Expected:** List of notebooks with counts (owned, shared).

---

### Test 1.4 - Create Notebook
**Tool:** `notebook_create`

**Prompt:**
```
Create a new notebook titled "MCP Test Notebook".
```

**Expected:** New notebook created with `notebook_id` and URL.

**Save:** Note the `notebook_id` for subsequent tests.

---

### Test 1.5 - Get Notebook Details
**Tool:** `notebook_get`

**Prompt:**
```
Get the details of notebook [notebook_id from Test 1.4].
```

**Expected:** Notebook details with empty sources list, timestamps.

---

### Test 1.6 - Rename Notebook
**Tool:** `notebook_rename`

**Prompt:**
```
Rename notebook [notebook_id] to "MCP Test - Renamed".
```

**Expected:** Success with updated title.

---

## Test Group 2: Adding Sources (Consolidated source_add)

### Test 2.1 - Add URL Source
**Tool:** `source_add`

**Prompt:**
```
Add a URL source to notebook [notebook_id]:
- source_type: url
- url: https://en.wikipedia.org/wiki/Artificial_intelligence
```

**Expected:** Source added with `source_id`, `source_type: url`.

---

### Test 2.2 - Add Text Source
**Tool:** `source_add`

**Prompt:**
```
Add a text source to notebook [notebook_id]:
- source_type: text
- title: "Test Document"
- text: "This is a test document about machine learning. Machine learning is a subset of artificial intelligence."
```

**Expected:** Text source added with `source_id`, `source_type: text`.

---

### Test 2.3 - Add Drive Source (Optional)
**Tool:** `source_add`

**Prompt:**
```
Add a Drive document to notebook [notebook_id]:
- source_type: drive
- document_id: [your_doc_id]
- title: "My Drive Doc"
- doc_type: doc
```

**Expected:** Drive source added (or skip if no Drive doc available).

---

### Test 2.4 - Add File Source (Optional)
**Tool:** `source_add`

**Prompt:**
```
Add a file to notebook [notebook_id]:
- source_type: file
- file_path: /path/to/document.pdf
```

**Expected:** File uploaded with `source_id`, `method: resumable`.

---

### Test 2.5 - List Sources with Drive Status
**Tool:** `source_list_drive`

**Prompt:**
```
List all sources in notebook [notebook_id] and check their Drive freshness status.
```

**Expected:** List showing sources by type, Drive sources show freshness.

**Save:** Note a `source_id` for next tests.

---

### Test 2.6 - Describe Source
**Tool:** `source_describe`

**Prompt:**
```
Get an AI-generated summary of source [source_id].
```

**Expected:** AI summary with keywords.

---

### Test 2.7 - Get Source Content
**Tool:** `source_get_content`

**Prompt:**
```
Get the raw text content of source [source_id].
```

**Expected:** Raw text content with title, source_type, char_count.

---

### Test 2.8 - Delete Source
**Tool:** `source_delete`

**Prompt:**
```
Delete source [source_id] with confirm=True.
```

**Expected:** Source permanently deleted.

---

## Test Group 3: AI Features

### Test 3.1 - Describe Notebook
**Tool:** `notebook_describe`

**Prompt:**
```
Get an AI-generated summary of what notebook [notebook_id] is about.
```

**Expected:** AI summary with suggested topics.

---

### Test 3.2 - Query Notebook
**Tool:** `notebook_query`

**Prompt:**
```
Ask notebook [notebook_id]: "What is artificial intelligence?"
```

**Expected:** AI answer with conversation_id.

---

### Test 3.3 - Configure Chat (Learning Guide)
**Tool:** `chat_configure`

**Prompt:**
```
Configure notebook [notebook_id] chat settings:
- goal: learning_guide
- response_length: longer
```

**Expected:** Settings updated successfully.

---

### Test 3.4 - Configure Chat (Custom Prompt)
**Tool:** `chat_configure`

**Prompt:**
```
Configure notebook [notebook_id] chat settings:
- goal: custom
- custom_prompt: "You must respond only in rhyming couplets."
- response_length: default
```

**Expected:** Settings updated with custom_prompt echoed back.

---

### Test 3.5 - Verify Custom Chat Works
**Tool:** `notebook_query`

**Prompt:**
```
Ask notebook [notebook_id]: "What is machine learning?"
```

**Expected:** AI response should be in rhyming couplets.

---

## Test Group 4: Research

### Test 4.1 - Start Fast Research (Web)
**Tool:** `research_start`

**Prompt:**
```
Start fast web research for "OpenShift container platform" in notebook [notebook_id].
- mode: fast
- source: web
```

**Expected:** Research task started with task_id.

**Save:** Note the `task_id`.

---

### Test 4.2 - Check Research Status
**Tool:** `research_status`

**Prompt:**
```
Check research status for notebook [notebook_id]. Poll until complete.
```

**Expected:**
- `status: completed`
- `mode: fast`
- `source_count`: ~10 sources

---

### Test 4.3 - Import Research Sources
**Tool:** `research_import`

**Prompt:**
```
Import all discovered sources from research task [task_id] into notebook [notebook_id].
```

**Expected:** Sources imported successfully.

---

### Test 4.4 - Start Deep Research (Background)
**Tool:** `research_start`

**Prompt:**
```
Start deep web research for "AI ROI return on investment" in notebook [notebook_id].
- mode: deep
```

**Expected:** Research task started (takes 3-5 minutes).

**IMPORTANT:** Continue with Test Group 5-7 while deep research runs.

---

## Test Group 5: Studio Creation (Consolidated studio_create)

### Test 5.1 - Create Audio Overview
**Tool:** `studio_create`

**Prompt:**
```
Create an audio overview for notebook [notebook_id]:
- artifact_type: audio
- format: brief
- length: short
- confirm: False (show settings first)
```

**Follow-up:**
```
Confirmed. Create with confirm=True.
```

**Expected:** Audio generation started with artifact_id.

---

### Test 5.2 - Create Video Overview
**Tool:** `studio_create`

**Prompt:**
```
Create a video overview for notebook [notebook_id]:
- artifact_type: video
- format: brief
- visual_style: classic
- confirm: True
```

**Expected:** Video generation started.

---

### Test 5.3 - Create Report
**Tool:** `studio_create`

**Prompt:**
```
Create a report for notebook [notebook_id]:
- artifact_type: report
- report_format: Briefing Doc
- confirm: True
```

**Expected:** Report generation started.

---

### Test 5.4 - Create Flashcards
**Tool:** `studio_create`

**Prompt:**
```
Create flashcards for notebook [notebook_id]:
- artifact_type: flashcards
- difficulty: medium
- confirm: True
```

**Expected:** Flashcards generation started.

---

### Test 5.5 - Create Quiz
**Tool:** `studio_create`

**Prompt:**
```
Create a quiz for notebook [notebook_id]:
- artifact_type: quiz
- question_count: 2
- difficulty: medium
- confirm: True
```

**Expected:** Quiz generation started.

---

### Test 5.6 - Create Infographic
**Tool:** `studio_create`

**Prompt:**
```
Create an infographic for notebook [notebook_id]:
- artifact_type: infographic
- orientation: landscape
- detail_level: standard
- confirm: True
```

**Expected:** Infographic generation started.

---

### Test 5.7 - Create Slide Deck
**Tool:** `studio_create`

**Prompt:**
```
Create a slide deck for notebook [notebook_id]:
- artifact_type: slide_deck
- format: detailed_deck
- length: short
- confirm: True
```

**Expected:** Slide deck generation started.

---

### Test 5.8 - Create Mind Map
**Tool:** `studio_create`

**Prompt:**
```
Create a mind map for notebook [notebook_id]:
- artifact_type: mind_map
- title: "AI Concepts"
- confirm: True
```

**Expected:** Mind map created immediately.

---

### Test 5.9 - Create Data Table
**Tool:** `studio_create`

**Prompt:**
```
Create a data table for notebook [notebook_id]:
- artifact_type: data_table
- description: "Key features and capabilities"
- confirm: True
```

**Expected:** Data table generation started.

---

### Test 5.10 - Check Studio Status
**Tool:** `studio_status`

**Prompt:**
```
Check studio content generation status for notebook [notebook_id].
```

**Expected:** List of artifacts with status (in_progress/completed) and URLs.

---

### Test 5.11 - Rename Studio Artifact
**Tool:** `studio_status` (with action="rename")

**Prompt:**
```
Rename artifact [artifact_id] in notebook [notebook_id] to "My Renamed Podcast".
- action: rename
- artifact_id: [artifact_id from studio_status]
- new_title: "My Renamed Podcast"
```

**Expected:** Artifact renamed successfully.

---

## Test Group 6: Downloads (Consolidated download_artifact)

### Test 6.1 - Download Report
**Tool:** `download_artifact`

**Prompt:**
```
Download the report from notebook [notebook_id]:
- artifact_type: report
- output_path: /tmp/report.md
```

**Expected:** Report downloaded as markdown.

---

### Test 6.2 - Download Flashcards (JSON)
**Tool:** `download_artifact`

**Prompt:**
```
Download flashcards from notebook [notebook_id]:
- artifact_type: flashcards
- output_path: /tmp/flashcards.json
- output_format: json
```

**Expected:** Flashcards downloaded as JSON.

---

### Test 6.3 - Download Quiz (Markdown)
**Tool:** `download_artifact`

**Prompt:**
```
Download quiz from notebook [notebook_id]:
- artifact_type: quiz
- output_path: /tmp/quiz.md
- output_format: markdown
```

**Expected:** Quiz downloaded as markdown.

---

### Test 6.4 - Download Audio
**Tool:** `download_artifact`

**Prompt:**
```
Download audio from notebook [notebook_id]:
- artifact_type: audio
- output_path: /tmp/podcast.mp4
```

**Expected:** Audio downloaded as MP4.

---

### Test 6.5 - Download Slide Deck
**Tool:** `download_artifact`

**Prompt:**
```
Download slide deck from notebook [notebook_id]:
- artifact_type: slide_deck
- output_path: /tmp/slides.pdf
```

**Expected:** Slides downloaded as PDF.

---

## Test Group 7: Sharing

### Test 7.1 - Get Share Status
**Tool:** `notebook_share_status`

**Prompt:**
```
Get sharing status for notebook [notebook_id].
```

**Expected:** Status with `is_public`, `access_level`, `collaborators`.

---

### Test 7.2 - Enable Public Link
**Tool:** `notebook_share_public`

**Prompt:**
```
Enable public link for notebook [notebook_id].
- is_public: True
```

**Expected:** Public link returned.

---

### Test 7.3 - Disable Public Link
**Tool:** `notebook_share_public`

**Prompt:**
```
Disable public link for notebook [notebook_id].
- is_public: False
```

**Expected:** Public link disabled.

---

### Test 7.4 - Invite Collaborator (Optional)
**Tool:** `notebook_share_invite`

**Prompt:**
```
Invite collaborator to notebook [notebook_id]:
- email: test@example.com
- role: viewer
```

**Expected:** Invitation sent (or error if email invalid).

---

## Test Group 8: Drive Sync (Optional)

### Test 8.1 - Sync Drive Sources
**Tool:** `source_sync_drive`

**Prompt:**
```
Check if any Drive sources in notebook [notebook_id] are stale using source_list_drive.
If any are stale, sync them using source_sync_drive with confirm=True.
```

**Expected:** Sources synced if any were stale.

---

## Test Group 9: Deep Research Verification

**TIMING:** By now, deep research from Test 4.4 should be complete.

### Test 9.1 - Check Deep Research Status
**Tool:** `research_status`

**Prompt:**
```
Check deep research status for notebook [notebook_id] with max_wait=60.
```

**Expected:**
- `status: completed`
- `mode: deep`
- `source_count`: ~40-50 sources
- `report` field present

---

### Test 9.2 - Import Deep Research Sources
**Tool:** `research_import`

**Prompt:**
```
Import all deep research sources from task [task_id] into notebook [notebook_id].
```

**Expected:** Sources imported successfully.

---

## Test Group 10: Cleanup

### Test 10.1 - Delete Studio Artifacts
**Tool:** `studio_delete`

**Prompt:**
```
Get studio status for notebook [notebook_id], then delete each artifact with confirm=True.
```

**Expected:** All artifacts deleted.

---

### Test 10.2 - Delete All Sources
**Tool:** `source_delete`

**Prompt:**
```
List sources in notebook [notebook_id], then delete each with confirm=True.
```

**Expected:** All sources deleted.

---

### Test 10.3 - Delete Notebook
**Tool:** `notebook_delete`

**Prompt:**
```
Delete notebook [notebook_id] with confirm=True.
```

**Expected:** Notebook deleted successfully.

---

## Test Group 11: Notes Management (Unified `note` tool)

### Test 11.1 - Create Note
**Tool:** `note`

**Prompt:**
```
Create a note in notebook [notebook_id]:
- action: create
- content: "This is a test note about AI"
- title: "AI Note"
```

**Expected:** Note created with `note_id`.

**Save:** Note the `note_id` for subsequent tests.

---

### Test 11.2 - List Notes
**Tool:** `note`

**Prompt:**
```
List all notes in notebook [notebook_id]:
- action: list
```

**Expected:** Array of notes including the one just created, with previews.

---

### Test 11.3 - Update Note
**Tool:** `note`

**Prompt:**
```
Update note [note_id] in notebook [notebook_id]:
- action: update
- note_id: [note_id]
- content: "Updated: AI is transforming technology"
```

**Expected:** Success confirmation.

---

### Test 11.4 - Delete Note
**Tool:** `note`

**Prompt:**
```
Delete note [note_id] in notebook [notebook_id]:
- action: delete
- note_id: [note_id]
- confirm: True
```

**Expected:** Deletion confirmation message.

---

## Test Group 12: Server Info

### Test 12.1 - Get Server Info
**Tool:** `server_info`

**Prompt:**
```
Get NotebookLM MCP server version and check for updates.
```

**Expected:**
- `version`: Current version
- `latest_version`: Latest PyPI version (or null if offline)
- `update_available`: Boolean
- `update_command`: Upgrade command

---

## Summary: 29 Consolidated Tools

| Category | Tools | Count |
|----------|-------|-------|
| **Auth** | `refresh_auth`, `save_auth_tokens` | 2 |
| **Notebooks** | `notebook_list`, `notebook_get`, `notebook_describe`, `notebook_create`, `notebook_rename`, `notebook_delete` | 6 |
| **Sources** | `source_add`, `source_list_drive`, `source_sync_drive`, `source_delete`, `source_describe`, `source_get_content` | 6 |
| **Sharing** | `notebook_share_status`, `notebook_share_public`, `notebook_share_invite` | 3 |
| **Research** | `research_start`, `research_status`, `research_import` | 3 |
| **Studio** | `studio_create`, `studio_status`, `studio_delete` | 3 |
| **Downloads** | `download_artifact` | 1 |
| **Exports** | `export_artifact` | 1 |
| **Chat** | `notebook_query`, `chat_configure` | 2 |
| **Notes** | `note` (unified: list, create, update, delete) | 1 |
| **Server** | `server_info` | 1 |
| **Total** | | **29** |

---

## Quick Copy-Paste Test Prompts

```
1. Refresh auth tokens
2. List all my NotebookLM notebooks
3. Create a new notebook titled "MCP Test Notebook"
4. Get details of notebook [id]
5. Rename notebook [id] to "MCP Test - Renamed"
6. Add URL source to notebook [id]: source_type=url, url=https://en.wikipedia.org/wiki/Artificial_intelligence
7. Add text source to notebook [id]: source_type=text, text="Machine learning test document"
8. List sources in notebook [id] with Drive status
9. Get AI summary of source [source_id]
10. Get raw text content of source [source_id]
11. Get AI summary of notebook [id]
12. Ask notebook [id]: "What is artificial intelligence?"
13. Configure notebook [id] chat: goal=learning_guide, response_length=longer
14. Configure notebook [id] chat: goal=custom, custom_prompt="Respond in rhymes"
15. Start fast web research for "OpenShift" in notebook [id]
16. Check research status for notebook [id]
17. Import research sources from task [task_id]
18. Start DEEP web research for "AI ROI" in notebook [id]
19. Create audio overview: artifact_type=audio, format=brief, confirm=True
20. Create video overview: artifact_type=video, format=brief, confirm=True
21. Check studio status for notebook [id]
22. Create report: artifact_type=report, report_format="Briefing Doc", confirm=True
23. Create flashcards: artifact_type=flashcards, confirm=True
24. Create quiz: artifact_type=quiz, question_count=2, confirm=True
25. Create infographic: artifact_type=infographic, confirm=True
26. Create slide deck: artifact_type=slide_deck, confirm=True
27. Create mind map: artifact_type=mind_map, title="AI Concepts", confirm=True
28. Download report: artifact_type=report, output_path=/tmp/report.md
29. Download flashcards: artifact_type=flashcards, output_path=/tmp/cards.json
30. Get share status for notebook [id]
31. Enable public link for notebook [id]
32. Check deep research status
33. Import deep research sources
34. Create note in notebook [id]: content="Test note", title="My Note"
35. List all notes in notebook [id]
36. Update note [note_id] in notebook [id]: content="Updated content"
37. Delete note [note_id] in notebook [id] with confirm=True
38. Delete all studio artifacts with confirm=True
39. Delete all sources with confirm=True
40. Delete notebook [id] with confirm=True
```
