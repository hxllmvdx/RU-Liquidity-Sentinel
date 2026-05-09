package redis

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"time"

	goredis "github.com/redis/go-redis/v9"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
)

func (c *Cache) GetDashboard(ctx context.Context, includeShap, includeForecast, includeComment bool) (*dto.DashboardResponse, error) {
	var payload dto.DashboardResponse
	found, err := c.getJSON(ctx, DashboardCurrentKey(includeShap, includeForecast, includeComment), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetDashboard(ctx context.Context, includeShap, includeForecast, includeComment bool, payload *dto.DashboardResponse) error {
	return c.setJSON(ctx, DashboardCurrentKey(includeShap, includeForecast, includeComment), payload, c.cfg.DashboardTTL)
}

func (c *Cache) GetLatestLSI(ctx context.Context) (*domain.LSIValue, error) {
	var payload domain.LSIValue
	found, err := c.getJSON(ctx, LatestLSIKey(), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetLatestLSI(ctx context.Context, payload *domain.LSIValue) error {
	return c.setJSON(ctx, LatestLSIKey(), payload, c.cfg.LSITTL)
}

func (c *Cache) GetLSIHistory(ctx context.Context, from, to string, limit, offset int) (*dto.LSIHistoryResponse, error) {
	var payload dto.LSIHistoryResponse
	found, err := c.getJSON(ctx, LSIHistoryKey(from, to, limit, offset), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetLSIHistory(ctx context.Context, from, to string, limit, offset int, payload *dto.LSIHistoryResponse) error {
	return c.setJSON(ctx, LSIHistoryKey(from, to, limit, offset), payload, c.cfg.HistoryTTL)
}

func (c *Cache) GetModulesSnapshot(ctx context.Context, date string) (*dto.ModulesSnapshotResponse, error) {
	var payload dto.ModulesSnapshotResponse
	found, err := c.getJSON(ctx, ModulesSnapshotKey(date), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetModulesSnapshot(ctx context.Context, date string, payload *dto.ModulesSnapshotResponse) error {
	return c.setJSON(ctx, ModulesSnapshotKey(date), payload, c.cfg.ModulesTTL)
}

func (c *Cache) GetModuleSignals(ctx context.Context, moduleID, from, to string) (*dto.ModuleSignalsResponse, error) {
	var payload dto.ModuleSignalsResponse
	found, err := c.getJSON(ctx, ModuleSignalsKey(moduleID, from, to), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetModuleSignals(ctx context.Context, moduleID, from, to string, payload *dto.ModuleSignalsResponse) error {
	return c.setJSON(ctx, ModuleSignalsKey(moduleID, from, to), payload, c.cfg.ModuleSignalsTTL)
}

func (c *Cache) GetBacktest(ctx context.Context, req dto.BacktestRequest, from, to string) (*dto.BacktestResponse, error) {
	var payload dto.BacktestResponse
	found, err := c.getJSON(ctx, BacktestKey(req.Episode, from, to, req.IncludeShap, req.IncludeModuleBreakdown), &payload)
	if !found || err != nil {
		return nil, err
	}
	return &payload, nil
}

func (c *Cache) SetBacktest(ctx context.Context, req dto.BacktestRequest, from, to string, payload *dto.BacktestResponse) error {
	return c.setJSON(ctx, BacktestKey(req.Episode, from, to, req.IncludeShap, req.IncludeModuleBreakdown), payload, c.cfg.BacktestTTL)
}

func (c *Cache) SetJobStatus(ctx context.Context, job domain.RecalculationJob) error {
	return c.setJSON(ctx, JobStatusKey(job.ID.String()), job, c.cfg.JobTTL)
}

func (c *Cache) InvalidateDashboard(ctx context.Context) error {
	return c.deleteByPattern(ctx, DashboardCurrentPattern())
}

func (c *Cache) InvalidateLatestLSI(ctx context.Context) error {
	return c.delete(ctx, LatestLSIKey())
}

func (c *Cache) InvalidateModulesSnapshot(ctx context.Context) error {
	return c.deleteByPattern(ctx, ModulesSnapshotPattern())
}

func (c *Cache) InvalidateModuleSignals(ctx context.Context) error {
	return c.deleteByPattern(ctx, ModuleSignalsPattern())
}

func (c *Cache) InvalidateLSIHistory(ctx context.Context) error {
	return c.deleteByPattern(ctx, keyPrefix+":lsi:history:*")
}

func (c *Cache) getJSON(ctx context.Context, key string, target any) (bool, error) {
	if !c.Enabled() {
		return false, nil
	}

	raw, err := c.client.Get(ctx, key).Bytes()
	if err != nil {
		if errors.Is(err, goredis.Nil) {
			return false, nil
		}
		log.Printf("redis get error key=%s err=%v", key, err)
		return false, err
	}

	if err := json.Unmarshal(raw, target); err != nil {
		log.Printf("redis unmarshal error key=%s err=%v", key, err)
		return false, nil
	}

	return true, nil
}

func (c *Cache) setJSON(ctx context.Context, key string, payload any, ttl time.Duration) error {
	if !c.Enabled() {
		return nil
	}

	if ttl <= 0 {
		ttl = c.cfg.DefaultTTL
	}

	raw, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	if err := c.client.Set(ctx, key, raw, ttl).Err(); err != nil {
		log.Printf("redis set error key=%s err=%v", key, err)
		return err
	}

	return nil
}

func (c *Cache) delete(ctx context.Context, key string) error {
	if !c.Enabled() {
		return nil
	}
	if err := c.client.Del(ctx, key).Err(); err != nil {
		log.Printf("redis delete error key=%s err=%v", key, err)
		return err
	}
	return nil
}

func (c *Cache) deleteByPattern(ctx context.Context, pattern string) error {
	if !c.Enabled() {
		return nil
	}

	var cursor uint64
	for {
		keys, nextCursor, err := c.client.Scan(ctx, cursor, pattern, 100).Result()
		if err != nil {
			log.Printf("redis scan error pattern=%s err=%v", pattern, err)
			return err
		}
		if len(keys) > 0 {
			if err := c.client.Del(ctx, keys...).Err(); err != nil {
				log.Printf("redis bulk delete error pattern=%s err=%v", pattern, err)
				return err
			}
		}
		cursor = nextCursor
		if cursor == 0 {
			return nil
		}
	}
}
