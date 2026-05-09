package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type LSIRepository struct {
	db *DB
}

func NewLSIRepository(db *DB) *LSIRepository {
	return &LSIRepository{db: db}
}

func (r *LSIRepository) SaveLSIValue(ctx context.Context, value domain.LSIValue) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `INSERT INTO lsi_values (calculation_date, lsi, status, confidence, auto_comment, model_version, calculated_at)
	VALUES ($1, $2, $3, $4, $5, $6, $7)
	ON CONFLICT (calculation_date) DO UPDATE SET
		lsi = EXCLUDED.lsi,
		status = EXCLUDED.status,
		confidence = EXCLUDED.confidence,
		auto_comment = EXCLUDED.auto_comment,
		model_version = EXCLUDED.model_version,
		calculated_at = EXCLUDED.calculated_at`
	_, err := r.db.conn.ExecContext(ctx, query, value.CalculationDate, value.LSI, value.Status, value.Confidence, value.AutoComment, value.ModelVersion, value.CalculatedAt)
	if err != nil {
		return fmt.Errorf("save lsi value: %w", err)
	}

	return nil
}

func (r *LSIRepository) GetLatestLSI(ctx context.Context) (*domain.LSIValue, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `SELECT id, calculation_date, lsi, status, confidence, auto_comment, model_version, calculated_at, created_at, updated_at
	FROM lsi_values
	ORDER BY calculation_date DESC
	LIMIT 1`

	var row lsiValueRow
	err := r.db.conn.GetContext(ctx, &row, query)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("get latest lsi: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}

func (r *LSIRepository) GetLSIHistory(ctx context.Context, from, to time.Time, limit, offset int) ([]domain.LSIValue, error) {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	const query = `SELECT id, calculation_date, lsi, status, confidence, auto_comment, model_version, calculated_at, created_at, updated_at
	FROM lsi_values
	WHERE calculation_date BETWEEN $1 AND $2
	ORDER BY calculation_date DESC
	LIMIT $3 OFFSET $4`

	var rows []lsiValueRow
	err := r.db.conn.SelectContext(ctx, &rows, query, from, to, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("get lsi history: %w", err)
	}

	results := make([]domain.LSIValue, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}

	return results, nil
}
