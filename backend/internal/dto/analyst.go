package dto

type GenerateAutoCommentRequest struct {
	Date                string       `json:"date"`
	LSI                 float64      `json:"lsi"`
	Status              string       `json:"status"`
	ModuleContributions []NamedValue `json:"module_contributions"`
	ActiveFlags         []string     `json:"active_flags"`
	UpcomingEvents      []string     `json:"upcoming_events"`
}

type AutoCommentResponse struct {
	Comment       string `json:"comment"`
	Retrospective string `json:"retrospective"`
	Outlook       string `json:"outlook"`
}

type ChatRequest struct {
	SessionID      string     `json:"session_id"`
	UserMessage    string     `json:"user_message"`
	PreferredRange *DateRange `json:"preferred_range,omitempty"`
}

type ChatContext struct {
	SourceType string  `json:"source_type"`
	Title      string  `json:"title"`
	Content    string  `json:"content"`
	Relevance  float64 `json:"relevance"`
}

type ChatResponse struct {
	SessionID string        `json:"session_id"`
	Answer    string        `json:"answer"`
	Contexts  []ChatContext `json:"contexts"`
}
