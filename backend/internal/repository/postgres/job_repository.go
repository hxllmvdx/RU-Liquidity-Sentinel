package postgres

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type JobRepository struct {
	db *DB
}

func NewJobRepository(db *DB) *JobRepository {
	return &JobRepository{db: db}
}

func (r *JobRepository) CreateJob(ctx context.Context, job domain.RecalculationJob) (*domain.RecalculationJob, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO recalculation_jobs (requested_date, status, force_reload_sources, recalculate_shap, regenerate_comment, started_at, finished_at, error_message, updated_sources, result_lsi_value_id)
	VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	RETURNING id, requested_date, status, force_reload_sources, recalculate_shap, regenerate_comment, started_at, finished_at, error_message, updated_sources, result_lsi_value_id, created_at, updated_at`

	var row recalculationJobRow
	if err := r.db.conn.GetContext(ctx, &row, query,
		job.RequestedDate,
		job.Status,
		job.ForceReloadSources,
		job.RecalculateShap,
		job.RegenerateComment,
		job.StartedAt,
		job.FinishedAt,
		job.ErrorMessage,
		job.UpdatedSources,
		job.ResultLSIValueID,
	); err != nil {
		return nil, fmt.Errorf("create job: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}

func (r *JobRepository) MarkJobRunning(ctx context.Context, jobID uuid.UUID) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `UPDATE recalculation_jobs
	SET status = 'running', started_at = now()
	WHERE id = $1`

	if _, err := r.db.conn.ExecContext(ctx, query, jobID); err != nil {
		return fmt.Errorf("mark job running: %w", err)
	}

	return nil
}

func (r *JobRepository) MarkJobSuccess(ctx context.Context, jobID uuid.UUID, resultLSIValueID *uuid.UUID, updatedSources []string) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	payload, err := json.Marshal(updatedSources)
	if err != nil {
		return fmt.Errorf("marshal updated sources: %w", err)
	}

	const query = `UPDATE recalculation_jobs
	SET status = 'success', finished_at = now(), error_message = NULL, result_lsi_value_id = $2, updated_sources = $3
	WHERE id = $1`

	if _, err := r.db.conn.ExecContext(ctx, query, jobID, resultLSIValueID, payload); err != nil {
		return fmt.Errorf("mark job success: %w", err)
	}

	return nil
}

func (r *JobRepository) MarkJobFailure(ctx context.Context, jobID uuid.UUID, errorMessage string) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `UPDATE recalculation_jobs
	SET status = 'failed', finished_at = now(), error_message = $2
	WHERE id = $1`

	if _, err := r.db.conn.ExecContext(ctx, query, jobID, errorMessage); err != nil {
		return fmt.Errorf("mark job failure: %w", err)
	}

	return nil
}

func (r *JobRepository) GetLastJob(ctx context.Context) (*domain.RecalculationJob, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	const query = `SELECT id, requested_date, status, force_reload_sources, recalculate_shap, regenerate_comment, started_at, finished_at, error_message, updated_sources, result_lsi_value_id, created_at, updated_at
	FROM recalculation_jobs
	ORDER BY created_at DESC
	LIMIT 1`

	var row recalculationJobRow
	if err := r.db.conn.GetContext(ctx, &row, query); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("get last job: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}
