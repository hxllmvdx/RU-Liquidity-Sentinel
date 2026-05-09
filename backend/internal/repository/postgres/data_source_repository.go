package postgres

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type DataSourceRepository struct {
	db *DB
}

func NewDataSourceRepository(db *DB) *DataSourceRepository {
	return &DataSourceRepository{db: db}
}

func (r *DataSourceRepository) GetActiveSources(ctx context.Context) ([]domain.DataSource, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, source_code, name, url, source_type, update_frequency, is_active, last_loaded_at, last_status, last_error, created_at, updated_at
	FROM data_sources
	WHERE is_active = true
	ORDER BY source_code ASC`

	var rows []dataSourceRow
	if err := r.db.conn.SelectContext(ctx, &rows, query); err != nil {
		return nil, fmt.Errorf("get active data sources: %w", err)
	}

	results := make([]domain.DataSource, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}

	return results, nil
}

func (r *DataSourceRepository) GetAllSources(ctx context.Context) ([]domain.DataSource, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, source_code, name, url, source_type, update_frequency, is_active, last_loaded_at, last_status, last_error, created_at, updated_at
	FROM data_sources
	ORDER BY source_code ASC`

	var rows []dataSourceRow
	if err := r.db.conn.SelectContext(ctx, &rows, query); err != nil {
		return nil, fmt.Errorf("get all data sources: %w", err)
	}

	results := make([]domain.DataSource, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}

	return results, nil
}

func (r *DataSourceRepository) GetSourceByCode(ctx context.Context, sourceCode string) (*domain.DataSource, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `SELECT id, source_code, name, url, source_type, update_frequency, is_active, last_loaded_at, last_status, last_error, created_at, updated_at
	FROM data_sources
	WHERE source_code = $1`

	var row dataSourceRow
	if err := r.db.conn.GetContext(ctx, &row, query, sourceCode); err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("get data source by code: %w", err)
		}
		return nil, fmt.Errorf("get data source by code: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}

func (r *DataSourceRepository) UpdateLoadSuccess(ctx context.Context, sourceCode string, loadedAt time.Time) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `UPDATE data_sources
	SET last_loaded_at = $2,
		last_status = 'success',
		last_error = NULL
	WHERE source_code = $1`

	result, err := r.db.conn.ExecContext(ctx, query, sourceCode, loadedAt)
	if err != nil {
		return fmt.Errorf("update data source load success: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("update data source load success rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return fmt.Errorf("update data source load success: %w", sql.ErrNoRows)
	}

	return nil
}

func (r *DataSourceRepository) UpdateLoadFailure(ctx context.Context, sourceCode string, errMessage string) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `UPDATE data_sources
	SET last_status = 'failed',
		last_error = $2
	WHERE source_code = $1`

	result, err := r.db.conn.ExecContext(ctx, query, sourceCode, errMessage)
	if err != nil {
		return fmt.Errorf("update data source load failure: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("update data source load failure rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return fmt.Errorf("update data source load failure: %w", sql.ErrNoRows)
	}

	return nil
}

func (r *DataSourceRepository) SetActive(ctx context.Context, sourceCode string, active bool) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `UPDATE data_sources
	SET is_active = $2
	WHERE source_code = $1`

	result, err := r.db.conn.ExecContext(ctx, query, sourceCode, active)
	if err != nil {
		return fmt.Errorf("set data source active: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("set data source active rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return fmt.Errorf("set data source active: %w", sql.ErrNoRows)
	}

	return nil
}

func (r *DataSourceRepository) UpsertSource(ctx context.Context, source domain.DataSource) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO data_sources (source_code, name, url, source_type, update_frequency, is_active)
	VALUES ($1, $2, $3, $4, $5, $6)
	ON CONFLICT (source_code) DO UPDATE SET
		name = EXCLUDED.name,
		url = EXCLUDED.url,
		source_type = EXCLUDED.source_type,
		update_frequency = EXCLUDED.update_frequency,
		is_active = EXCLUDED.is_active`

	if _, err := r.db.conn.ExecContext(ctx, query,
		source.SourceCode,
		source.Name,
		source.URL,
		source.SourceType,
		source.UpdateFrequency,
		source.IsActive,
	); err != nil {
		return fmt.Errorf("upsert data source: %w", err)
	}

	return nil
}
