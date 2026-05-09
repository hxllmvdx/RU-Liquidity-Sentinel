package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type ModulesRepository struct {
	db *DB
}

func NewModulesRepository(db *DB) *ModulesRepository {
	return &ModulesRepository{db: db}
}

func (r *ModulesRepository) SaveModuleSignals(ctx context.Context, signals []domain.ModuleSignal) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO module_signals (signal_date, module_id, signal_name, raw_value, mad_score, flag, unit, metadata)
	VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	ON CONFLICT (module_id, signal_name, signal_date) DO UPDATE SET
		raw_value = EXCLUDED.raw_value,
		mad_score = EXCLUDED.mad_score,
		flag = EXCLUDED.flag,
		unit = EXCLUDED.unit,
		metadata = EXCLUDED.metadata`

	for _, signal := range signals {
		if _, err := r.db.conn.ExecContext(ctx, query,
			signal.SignalDate,
			signal.ModuleID,
			signal.SignalName,
			signal.RawValue,
			signal.MADScore,
			signal.Flag,
			signal.Unit,
			signal.Metadata,
		); err != nil {
			return fmt.Errorf("save module signals: %w", err)
		}
	}

	return nil
}

func (r *ModulesRepository) GetModuleSignals(ctx context.Context, moduleID string, from, to time.Time) ([]domain.ModuleSignal, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, signal_date, module_id, signal_name, raw_value, mad_score, flag, unit, metadata, created_at
	FROM module_signals
	WHERE module_id = $1 AND signal_date BETWEEN $2 AND $3
	ORDER BY signal_date DESC, signal_name ASC`

	var rows []moduleSignalRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, moduleID, from, to); err != nil {
		return nil, fmt.Errorf("get module signals: %w", err)
	}

	results := make([]domain.ModuleSignal, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}

func (r *ModulesRepository) SaveActiveFlags(ctx context.Context, flags []domain.ActiveFlag) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO active_flags (flag_date, module_id, flag_name, description, severity)
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (flag_date, module_id, flag_name) DO UPDATE SET
		description = EXCLUDED.description,
		severity = EXCLUDED.severity`

	for _, flag := range flags {
		if _, err := r.db.conn.ExecContext(ctx, query,
			flag.FlagDate,
			flag.ModuleID,
			flag.FlagName,
			flag.Description,
			flag.Severity,
		); err != nil {
			return fmt.Errorf("save active flags: %w", err)
		}
	}

	return nil
}

func (r *ModulesRepository) GetActiveFlags(ctx context.Context, moduleID string, from, to time.Time) ([]domain.ActiveFlag, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, flag_date, module_id, flag_name, description, severity, created_at
	FROM active_flags
	WHERE module_id = $1 AND flag_date BETWEEN $2 AND $3
	ORDER BY flag_date DESC, flag_name ASC`

	var rows []activeFlagRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, moduleID, from, to); err != nil {
		return nil, fmt.Errorf("get active flags: %w", err)
	}

	results := make([]domain.ActiveFlag, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}
