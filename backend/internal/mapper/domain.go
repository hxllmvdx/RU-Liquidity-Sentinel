package mapper

import (
	"encoding/json"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
)

const dateLayout = "2006-01-02"

func DashboardResponseFromDomain(
	value domain.LSIValue,
	contributions []domain.ModuleContribution,
	shapValues []domain.ShapValue,
	activeFlags []domain.ActiveFlag,
	forecast []dto.ForecastPoint,
) *dto.DashboardResponse {
	return &dto.DashboardResponse{
		Date:          formatDate(value.CalculationDate),
		LSI:           value.LSI,
		Status:        value.Status,
		Confidence:    float64Value(value.Confidence),
		Contributions: ModuleContributionsFromDomain(contributions),
		ShapValues:    ShapValuesFromDomain(shapValues),
		ActiveFlags:   ActiveFlagsFromDomain(activeFlags),
		Forecast:      forecast,
		AutoComment:   stringValue(value.AutoComment),
	}
}

func LSIHistoryPointFromDomain(value domain.LSIValue) dto.LSIHistoryPoint {
	return dto.LSIHistoryPoint{
		Date:       formatDate(value.CalculationDate),
		LSI:        value.LSI,
		Status:     value.Status,
		Confidence: float64Value(value.Confidence),
	}
}

func LSIHistoryResponseFromDomain(values []domain.LSIValue) *dto.LSIHistoryResponse {
	points := make([]dto.LSIHistoryPoint, 0, len(values))
	for _, value := range values {
		points = append(points, LSIHistoryPointFromDomain(value))
	}
	return &dto.LSIHistoryResponse{Points: points}
}

func ModuleSignalFromDomain(signal domain.ModuleSignal) dto.ModuleSignal {
	return dto.ModuleSignal{
		Date:       formatDate(signal.SignalDate),
		ModuleID:   signal.ModuleID,
		SignalName: signal.SignalName,
		RawValue:   float64Value(signal.RawValue),
		MadScore:   float64Value(signal.MADScore),
		Flag:       signal.Flag,
		Unit:       stringValue(signal.Unit),
	}
}

func ModuleSignalsFromDomain(signals []domain.ModuleSignal) []dto.ModuleSignal {
	result := make([]dto.ModuleSignal, 0, len(signals))
	for _, signal := range signals {
		result = append(result, ModuleSignalFromDomain(signal))
	}
	return result
}

func ModuleSignalsResponseFromDomain(moduleID string, signals []domain.ModuleSignal, activeFlags []domain.ActiveFlag) *dto.ModuleSignalsResponse {
	return &dto.ModuleSignalsResponse{
		ModuleID:    moduleID,
		Signals:     ModuleSignalsFromDomain(signals),
		ActiveFlags: ActiveFlagsFromDomain(activeFlags),
	}
}

func ModuleContributionFromDomain(item domain.ModuleContribution) dto.ModuleContribution {
	return dto.ModuleContribution{
		ModuleID:            item.ModuleID,
		ModuleName:          item.ModuleName,
		ContributionValue:   item.ContributionValue,
		ContributionPercent: float64Value(item.ContributionPercent),
	}
}

func ModuleContributionsFromDomain(items []domain.ModuleContribution) []dto.ModuleContribution {
	result := make([]dto.ModuleContribution, 0, len(items))
	for _, item := range items {
		result = append(result, ModuleContributionFromDomain(item))
	}
	return result
}

func ShapValueFromDomain(item domain.ShapValue) dto.ShapValue {
	return dto.ShapValue{
		FeatureName: item.FeatureName,
		ModuleID:    item.ModuleID,
		Value:       item.Value,
		AbsValue:    item.AbsValue,
	}
}

func ShapValuesFromDomain(items []domain.ShapValue) []dto.ShapValue {
	result := make([]dto.ShapValue, 0, len(items))
	for _, item := range items {
		result = append(result, ShapValueFromDomain(item))
	}
	return result
}

func ActiveFlagFromDomain(item domain.ActiveFlag) dto.ActiveFlag {
	return dto.ActiveFlag{
		FlagName:    item.FlagName,
		ModuleID:    item.ModuleID,
		Description: stringValue(item.Description),
		Severity:    float64Value(item.Severity),
	}
}

func ActiveFlagsFromDomain(items []domain.ActiveFlag) []dto.ActiveFlag {
	result := make([]dto.ActiveFlag, 0, len(items))
	for _, item := range items {
		result = append(result, ActiveFlagFromDomain(item))
	}
	return result
}

func BacktestResponseFromDomain(result domain.BacktestResult) (*dto.BacktestResponse, error) {
	metrics, err := decodeJSONSlice[dto.BacktestMetric](result.Metrics)
	if err != nil {
		return nil, err
	}
	events, err := decodeJSONSlice[dto.BacktestEvent](result.Events)
	if err != nil {
		return nil, err
	}
	history, err := decodeJSONSlice[dto.LSIHistoryPoint](result.LSIHistory)
	if err != nil {
		return nil, err
	}
	contributions, err := decodeJSONSlice[dto.ModuleContribution](result.AverageContributions)
	if err != nil {
		return nil, err
	}

	return &dto.BacktestResponse{
		Episode:              result.Episode,
		Range:                dto.DateRange{From: formatDate(result.RangeFrom), To: formatDate(result.RangeTo)},
		LSIHistory:           history,
		Metrics:              metrics,
		Events:               events,
		AverageContributions: contributions,
		Conclusion:           stringValue(result.Conclusion),
	}, nil
}

func ChatResponseFromDomain(sessionID string, answer string, contexts []dto.ChatContext) *dto.ChatResponse {
	return &dto.ChatResponse{
		SessionID: sessionID,
		Answer:    answer,
		Contexts:  contexts,
	}
}

func ChatContextsFromMessage(message domain.ChatMessage) ([]dto.ChatContext, error) {
	return decodeJSONSlice[dto.ChatContext](message.Contexts)
}

func formatDate(value time.Time) string {
	if value.IsZero() {
		return ""
	}
	return value.Format(dateLayout)
}

func stringValue(value *string) string {
	if value == nil {
		return ""
	}
	return *value
}

func float64Value(value *float64) float64 {
	if value == nil {
		return 0
	}
	return *value
}

func decodeJSONSlice[T any](raw json.RawMessage) ([]T, error) {
	if len(raw) == 0 {
		return []T{}, nil
	}
	var result []T
	if err := json.Unmarshal(raw, &result); err != nil {
		return nil, err
	}
	return result, nil
}
