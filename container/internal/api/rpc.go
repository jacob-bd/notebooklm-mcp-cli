// Package api provides the HTTP client for the NotebookLM internal API.
package api

// RPC IDs for the NotebookLM batchexecute API.
// These are discovered by capturing network traffic from the web UI.
const (
	// Notebooks
	RPCListNotebooks  = "wXbhsf"
	RPCGetNotebook    = "rLM1Ne"
	RPCCreateNotebook = "CCqFvf"
	RPCUpdateNotebook = "s0tc2d" // Rename + configure chat (overloaded)
	RPCDeleteNotebook = "WWINqb"

	// Sources
	RPCAddSource    = "izAoDd"
	RPCGetSource    = "hizoJc"
	RPCSyncSource   = "FLmJqe"
	RPCDeleteSource = "tGMBJ"

	// Research
	RPCStartFastResearch = "Ljjv0c"
	RPCStartDeepResearch = "QA9ei"
	RPCPollResearch      = "e3bVqc"
	RPCImportSources     = "LBwxtb"

	// Studio (audio, video, reports, flashcards, infographics, slides, etc.)
	RPCCreateStudio = "R7cb6c"
	RPCPollStudio   = "gArtLc"
	RPCDeleteStudio = "V5N4be"
	RPCRenameStudio = "rc3d8d"

	// Mind maps and notes
	RPCSaveMindMap = "CYK0Xb" // Also: create note
	RPCListMindMaps    = "cFji9"  // Also: list notes
	RPCDeleteMindMap   = "AH0mwd" // Also: delete note

	// Notes (share RPCs with mind maps where noted)
	RPCUpdateNote = "cYAfTb"

	// Summaries and guides
	RPCNotebookSummary = "VfAZjd"
	RPCSourceGuide     = "tr032e"

	// Sharing
	RPCSetSharing    = "QDyure"
	RPCGetShareStatus = "JFMDGd"

	// Exports
	RPCExport = "Krh3pd"
)

// DefaultBuildLabel is the NotebookLM frontend build identifier.
// Updated periodically with new NotebookLM releases. Can be overridden
// via the NOTEBOOKLM_BL environment variable.
const DefaultBuildLabel = "boq_labs-tailwind-frontend_20260108.06_p0"

// BaseURL is the NotebookLM origin.
const BaseURL = "https://notebooklm.google.com"

// BatchExecutePath is the RPC endpoint path.
const BatchExecutePath = "/_/LabsTailwindUi/data/batchexecute"

// StreamQueryPath is the streaming query endpoint.
const StreamQueryPath = "/_/LabsTailwindUi/data/google.internal.labs.tailwind.orchestration.v1.LabsTailwindOrchestrationService/GenerateFreeFormStreamed"

// NotebookPath returns the source-path for a notebook.
func NotebookPath(notebookID string) string {
	return "/notebook/" + notebookID
}
