package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type ContributionsRepository struct {
	db *DB
}

func NewContributionsRepository(db *DB) *ContributionsRepository {
	return &ContributionsRepository{db: db}
}

func (r *ContributionsRepository) SaveModuleContributions(ctx context.Context, items []domain.ModuleContribution) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO module_contributions (lsi_value_id, module_id, module_name, contribution_value, contribution_percent)
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (lsi_value_id, module_id) DO UPDATE SET
		module_name = EXCLUDED.module_name,
		contribution_value = EXCLUDED.contribution_value,
		contribution_percent = EXCLUDED.contribution_percent`

	for _, item := range items {
		if _, err := r.db.conn.ExecContext(ctx, query,
			item.LSIValueID,
			item.ModuleID,
			item.ModuleName,
			item.ContributionValue,
			item.ContributionPercent,
		); err != nil {
			return fmt.Errorf("save module contributions: %w", err)
		}
	}

	return nil
}

func (r *ContributionsRepository) SaveShapValues(ctx context.Context, items []domain.ShapValue) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO shap_values (lsi_value_id, feature_name, module_id, value, abs_value)
	VALUES ($1, $2, $3, $4, $5)
	ON CONFLICT (lsi_value_id, feature_name) DO UPDATE SET
		module_id = EXCLUDED.module_id,
		value = EXCLUDED.value,
		abs_value = EXCLUDED.abs_value`

	for _, item := range items {
		if _, err := r.db.conn.ExecContext(ctx, query,
			item.LSIValueID,
			item.FeatureName,
			item.ModuleID,
			item.Value,
			item.AbsValue,
		); err != nil {
			return fmt.Errorf("save shap values: %w", err)
		}
	}

	return nil
}

func (r *ContributionsRepository) GetContributionsByLSI(ctx context.Context, lsiValueID uuid.UUID) ([]domain.ModuleContribution, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, lsi_value_id, module_id, module_name, contribution_value, contribution_percent, created_at
	FROM module_contributions
	WHERE lsi_value_id = $1
	ORDER BY module_id ASC`

	var rows []moduleContributionRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, lsiValueID); err != nil {
		return nil, fmt.Errorf("get contributions by lsi: %w", err)
	}

	results := make([]domain.ModuleContribution, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}

func (r *ContributionsRepository) GetShapValuesByLSI(ctx context.Context, lsiValueID uuid.UUID) ([]domain.ShapValue, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, lsi_value_id, feature_name, module_id, value, abs_value, created_at
	FROM shap_values
	WHERE lsi_value_id = $1
	ORDER BY abs_value DESC, feature_name ASC`

	var rows []shapValueRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, lsiValueID); err != nil {
		return nil, fmt.Errorf("get shap values by lsi: %w", err)
	}

	results := make([]domain.ShapValue, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}
