package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type BacktestRepository struct {
	db *DB
}

func NewBacktestRepository(db *DB) *BacktestRepository {
	return &BacktestRepository{db: db}
}

func (r *BacktestRepository) SaveBacktestResult(ctx context.Context, result domain.BacktestResult) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO backtest_results (episode, range_from, range_to, conclusion, metrics, events, lsi_history, average_contributions)
	VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`

	if _, err := r.db.conn.ExecContext(ctx, query,
		result.Episode,
		result.RangeFrom,
		result.RangeTo,
		result.Conclusion,
		result.Metrics,
		result.Events,
		result.LSIHistory,
		result.AverageContributions,
	); err != nil {
		return fmt.Errorf("save backtest result: %w", err)
	}

	return nil
}

func (r *BacktestRepository) GetBacktestResult(ctx context.Context, episode string, from, to time.Time) (*domain.BacktestResult, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, episode, range_from, range_to, conclusion, metrics, events, lsi_history, average_contributions, created_at, updated_at
	FROM backtest_results
	WHERE episode = $1 AND range_from = $2 AND range_to = $3
	LIMIT 1`

	var row backtestResultRow
	if err := r.db.conn.GetContext(ctx, &row, query, episode, from, to); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("get backtest result: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}
