package postgres

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type lsiValueRow struct {
	ID              uuid.UUID `db:"id"`
	CalculationDate time.Time `db:"calculation_date"`
	LSI             float64   `db:"lsi"`
	Status          string    `db:"status"`
	Confidence      *float64  `db:"confidence"`
	AutoComment     *string   `db:"auto_comment"`
	ModelVersion    *string   `db:"model_version"`
	CalculatedAt    time.Time `db:"calculated_at"`
	CreatedAt       time.Time `db:"created_at"`
	UpdatedAt       time.Time `db:"updated_at"`
}

func (r lsiValueRow) toDomain() domain.LSIValue {
	return domain.LSIValue{
		ID:              r.ID,
		CalculationDate: r.CalculationDate,
		LSI:             r.LSI,
		Status:          r.Status,
		Confidence:      r.Confidence,
		AutoComment:     r.AutoComment,
		ModelVersion:    r.ModelVersion,
		CalculatedAt:    r.CalculatedAt,
		CreatedAt:       r.CreatedAt,
		UpdatedAt:       r.UpdatedAt,
	}
}

type moduleSignalRow struct {
	ID         uuid.UUID       `db:"id"`
	SignalDate time.Time       `db:"signal_date"`
	ModuleID   string          `db:"module_id"`
	SignalName string          `db:"signal_name"`
	RawValue   *float64        `db:"raw_value"`
	MADScore   *float64        `db:"mad_score"`
	Flag       bool            `db:"flag"`
	Unit       *string         `db:"unit"`
	Metadata   json.RawMessage `db:"metadata"`
	CreatedAt  time.Time       `db:"created_at"`
}

func (r moduleSignalRow) toDomain() domain.ModuleSignal {
	return domain.ModuleSignal{
		ID:         r.ID,
		SignalDate: r.SignalDate,
		ModuleID:   r.ModuleID,
		SignalName: r.SignalName,
		RawValue:   r.RawValue,
		MADScore:   r.MADScore,
		Flag:       r.Flag,
		Unit:       r.Unit,
		Metadata:   r.Metadata,
		CreatedAt:  r.CreatedAt,
	}
}

type activeFlagRow struct {
	ID          uuid.UUID `db:"id"`
	FlagDate    time.Time `db:"flag_date"`
	ModuleID    string    `db:"module_id"`
	FlagName    string    `db:"flag_name"`
	Description *string   `db:"description"`
	Severity    *float64  `db:"severity"`
	CreatedAt   time.Time `db:"created_at"`
}

func (r activeFlagRow) toDomain() domain.ActiveFlag {
	return domain.ActiveFlag{
		ID:          r.ID,
		FlagDate:    r.FlagDate,
		ModuleID:    r.ModuleID,
		FlagName:    r.FlagName,
		Description: r.Description,
		Severity:    r.Severity,
		CreatedAt:   r.CreatedAt,
	}
}

type moduleContributionRow struct {
	ID                  uuid.UUID `db:"id"`
	LSIValueID          uuid.UUID `db:"lsi_value_id"`
	ModuleID            string    `db:"module_id"`
	ModuleName          string    `db:"module_name"`
	ContributionValue   float64   `db:"contribution_value"`
	ContributionPercent *float64  `db:"contribution_percent"`
	CreatedAt           time.Time `db:"created_at"`
}

func (r moduleContributionRow) toDomain() domain.ModuleContribution {
	return domain.ModuleContribution{
		ID:                  r.ID,
		LSIValueID:          r.LSIValueID,
		ModuleID:            r.ModuleID,
		ModuleName:          r.ModuleName,
		ContributionValue:   r.ContributionValue,
		ContributionPercent: r.ContributionPercent,
		CreatedAt:           r.CreatedAt,
	}
}

type shapValueRow struct {
	ID          uuid.UUID `db:"id"`
	LSIValueID  uuid.UUID `db:"lsi_value_id"`
	FeatureName string    `db:"feature_name"`
	ModuleID    string    `db:"module_id"`
	Value       float64   `db:"value"`
	AbsValue    float64   `db:"abs_value"`
	CreatedAt   time.Time `db:"created_at"`
}

func (r shapValueRow) toDomain() domain.ShapValue {
	return domain.ShapValue{
		ID:          r.ID,
		LSIValueID:  r.LSIValueID,
		FeatureName: r.FeatureName,
		ModuleID:    r.ModuleID,
		Value:       r.Value,
		AbsValue:    r.AbsValue,
		CreatedAt:   r.CreatedAt,
	}
}

type backtestResultRow struct {
	ID                   uuid.UUID       `db:"id"`
	Episode              string          `db:"episode"`
	RangeFrom            time.Time       `db:"range_from"`
	RangeTo              time.Time       `db:"range_to"`
	Conclusion           *string         `db:"conclusion"`
	Metrics              json.RawMessage `db:"metrics"`
	Events               json.RawMessage `db:"events"`
	LSIHistory           json.RawMessage `db:"lsi_history"`
	AverageContributions json.RawMessage `db:"average_contributions"`
	CreatedAt            time.Time       `db:"created_at"`
	UpdatedAt            time.Time       `db:"updated_at"`
}

func (r backtestResultRow) toDomain() domain.BacktestResult {
	return domain.BacktestResult{
		ID:                   r.ID,
		Episode:              r.Episode,
		RangeFrom:            r.RangeFrom,
		RangeTo:              r.RangeTo,
		Conclusion:           r.Conclusion,
		Metrics:              r.Metrics,
		Events:               r.Events,
		LSIHistory:           r.LSIHistory,
		AverageContributions: r.AverageContributions,
		CreatedAt:            r.CreatedAt,
		UpdatedAt:            r.UpdatedAt,
	}
}

type recalculationJobRow struct {
	ID                 uuid.UUID       `db:"id"`
	RequestedDate      *time.Time      `db:"requested_date"`
	Status             string          `db:"status"`
	ForceReloadSources bool            `db:"force_reload_sources"`
	RecalculateShap    bool            `db:"recalculate_shap"`
	RegenerateComment  bool            `db:"regenerate_comment"`
	StartedAt          *time.Time      `db:"started_at"`
	FinishedAt         *time.Time      `db:"finished_at"`
	ErrorMessage       *string         `db:"error_message"`
	UpdatedSources     json.RawMessage `db:"updated_sources"`
	ResultLSIValueID   *uuid.UUID      `db:"result_lsi_value_id"`
	CreatedAt          time.Time       `db:"created_at"`
	UpdatedAt          time.Time       `db:"updated_at"`
}

func (r recalculationJobRow) toDomain() domain.RecalculationJob {
	return domain.RecalculationJob{
		ID:                 r.ID,
		RequestedDate:      r.RequestedDate,
		Status:             r.Status,
		ForceReloadSources: r.ForceReloadSources,
		RecalculateShap:    r.RecalculateShap,
		RegenerateComment:  r.RegenerateComment,
		StartedAt:          r.StartedAt,
		FinishedAt:         r.FinishedAt,
		ErrorMessage:       r.ErrorMessage,
		UpdatedSources:     r.UpdatedSources,
		ResultLSIValueID:   r.ResultLSIValueID,
		CreatedAt:          r.CreatedAt,
		UpdatedAt:          r.UpdatedAt,
	}
}

type chatSessionRow struct {
	ID         uuid.UUID `db:"id"`
	SessionKey string    `db:"session_key"`
	Title      *string   `db:"title"`
	CreatedAt  time.Time `db:"created_at"`
	UpdatedAt  time.Time `db:"updated_at"`
}

func (r chatSessionRow) toDomain() domain.ChatSession {
	return domain.ChatSession{
		ID:         r.ID,
		SessionKey: r.SessionKey,
		Title:      r.Title,
		CreatedAt:  r.CreatedAt,
		UpdatedAt:  r.UpdatedAt,
	}
}

type chatMessageRow struct {
	ID        uuid.UUID       `db:"id"`
	SessionID uuid.UUID       `db:"session_id"`
	Role      string          `db:"role"`
	Content   string          `db:"content"`
	Contexts  json.RawMessage `db:"contexts"`
	CreatedAt time.Time       `db:"created_at"`
}

func (r chatMessageRow) toDomain() domain.ChatMessage {
	return domain.ChatMessage{
		ID:        r.ID,
		SessionID: r.SessionID,
		Role:      r.Role,
		Content:   r.Content,
		Contexts:  r.Contexts,
		CreatedAt: r.CreatedAt,
	}
}

type ragDocumentRow struct {
	ID         uuid.UUID       `db:"id"`
	SourceType string          `db:"source_type"`
	SourceID   *string         `db:"source_id"`
	Title      string          `db:"title"`
	Content    string          `db:"content"`
	Metadata   json.RawMessage `db:"metadata"`
	Embedding  []float32       `db:"embedding"`
	CreatedAt  time.Time       `db:"created_at"`
	UpdatedAt  time.Time       `db:"updated_at"`
}

func (r ragDocumentRow) toDomain() domain.RAGDocument {
	return domain.RAGDocument{
		ID:         r.ID,
		SourceType: r.SourceType,
		SourceID:   r.SourceID,
		Title:      r.Title,
		Content:    r.Content,
		Metadata:   r.Metadata,
		Embedding:  r.Embedding,
		CreatedAt:  r.CreatedAt,
		UpdatedAt:  r.UpdatedAt,
	}
}
