// Package constants provides bidirectional name-to-code mappings
// for the NotebookLM internal API.
package constants

import "strings"

// CodeMap is a bidirectional mapping between human-readable names
// and integer codes used by the NotebookLM API.
type CodeMap struct {
	nameToCode map[string]int
	codeToName map[int]string
}

// NewCodeMap creates a CodeMap from a name->code mapping.
// Names are stored lowercase for case-insensitive lookup.
func NewCodeMap(entries map[string]int) *CodeMap {
	m := &CodeMap{
		nameToCode: make(map[string]int, len(entries)),
		codeToName: make(map[int]string, len(entries)),
	}
	for name, code := range entries {
		m.nameToCode[strings.ToLower(name)] = code
		m.codeToName[code] = name
	}
	return m
}

// Code returns the integer code for a name. Case-insensitive.
func (m *CodeMap) Code(name string) (int, bool) {
	code, ok := m.nameToCode[strings.ToLower(name)]
	return code, ok
}

// Name returns the name for an integer code.
func (m *CodeMap) Name(code int) (string, bool) {
	name, ok := m.codeToName[code]
	return name, ok
}

// All known code mappings. These mirror the Python CodeMapper constants.

var ChatGoals = NewCodeMap(map[string]int{
	"default":        1,
	"custom":         2,
	"learning_guide": 3,
})

var ResponseLengths = NewCodeMap(map[string]int{
	"default": 1,
	"longer":  4,
	"shorter": 5,
})

var ResearchSources = NewCodeMap(map[string]int{
	"web":   1,
	"drive": 2,
})

var ResearchModes = NewCodeMap(map[string]int{
	"fast": 1,
	"deep": 5,
})

var SourceTypes = NewCodeMap(map[string]int{
	"google_docs":          1,
	"google_slides_sheets": 2,
	"pdf":                  3,
	"pasted_text":          4,
	"web_page":             5,
	"generated_text":       8,
	"youtube":              9,
	"uploaded_file":        11,
	"image":                13,
	"word_doc":             14,
})

var StudioTypes = NewCodeMap(map[string]int{
	"audio":       1,
	"report":      2,
	"video":       3,
	"flashcards":  4,
	"infographic": 7,
	"slide_deck":  8,
	"data_table":  9,
})

var AudioFormats = NewCodeMap(map[string]int{
	"deep_dive": 1,
	"brief":     2,
	"critique":  3,
	"debate":    4,
})

var AudioLengths = NewCodeMap(map[string]int{
	"short":   1,
	"default": 2,
	"long":    3,
})

var VideoFormats = NewCodeMap(map[string]int{
	"explainer": 1,
	"brief":     2,
})

var VideoStyles = NewCodeMap(map[string]int{
	"auto_select": 1,
	"custom":      2,
	"classic":     3,
	"whiteboard":  4,
	"kawaii":       5,
	"anime":       6,
	"watercolor":  7,
	"retro_print": 8,
	"heritage":    9,
	"paper_craft": 10,
})

var InfographicOrientations = NewCodeMap(map[string]int{
	"landscape": 1,
	"portrait":  2,
	"square":    3,
})

var InfographicDetails = NewCodeMap(map[string]int{
	"concise":  1,
	"standard": 2,
	"detailed": 3,
})

var SlideDeckFormats = NewCodeMap(map[string]int{
	"detailed_deck":    1,
	"presenter_slides": 2,
})

var SlideDeckLengths = NewCodeMap(map[string]int{
	"short":   1,
	"default": 3,
})

var FlashcardDifficulties = NewCodeMap(map[string]int{
	"easy":   1,
	"medium": 2,
	"hard":   3,
})

var ShareRoles = NewCodeMap(map[string]int{
	"owner":  1,
	"editor": 2,
	"viewer": 3,
})

var ShareAccess = NewCodeMap(map[string]int{
	"restricted": 0,
	"public":     1,
})

var ExportTypes = NewCodeMap(map[string]int{
	"docs":   1,
	"sheets": 2,
})
