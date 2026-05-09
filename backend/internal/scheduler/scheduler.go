package scheduler

import (
	"context"
	"fmt"
	"log"
	"sync"

	"github.com/robfig/cron/v3"
)

type Scheduler struct {
	cfg   Config
	cron  *cron.Cron
	job   *RecalculationJob
	wg    sync.WaitGroup
	entry cron.EntryID
}

func New(cfg Config, job *RecalculationJob) (*Scheduler, error) {
	parser := cron.NewParser(cron.Minute | cron.Hour | cron.Dom | cron.Month | cron.Dow)
	if _, err := parser.Parse(cfg.Cron); err != nil {
		return nil, fmt.Errorf("parse scheduler cron: %w", err)
	}

	c := cron.New(
		cron.WithLocation(cfg.Timezone),
		cron.WithParser(parser),
	)

	s := &Scheduler{
		cfg:  cfg,
		cron: c,
		job:  job,
	}

	entryID, err := c.AddFunc(cfg.Cron, func() {
		s.run(context.Background())
	})
	if err != nil {
		return nil, fmt.Errorf("register scheduler job: %w", err)
	}
	s.entry = entryID

	log.Printf("scheduler job registered cron=%q timezone=%s entry_id=%d", cfg.Cron, cfg.TimezoneName, entryID)
	return s, nil
}

func (s *Scheduler) Start(parent context.Context) {
	log.Printf("scheduler starting enabled=%t cron=%q timezone=%s run_on_startup=%t timeout=%s", s.cfg.Enabled, s.cfg.Cron, s.cfg.TimezoneName, s.cfg.RunOnStartup, s.cfg.Timeout)
	s.cron.Start()

	if s.cfg.RunOnStartup {
		go s.run(parent)
	}
}

func (s *Scheduler) Stop() context.Context {
	log.Printf("scheduler stopping entry_id=%d", s.entry)
	stopCtx := s.cron.Stop()
	s.wg.Wait()
	return stopCtx
}

func (s *Scheduler) run(parent context.Context) {
	s.wg.Add(1)
	defer s.wg.Done()
	s.job.Run(parent)
}
