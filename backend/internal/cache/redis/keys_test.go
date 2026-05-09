package redis

import "testing"

func TestKeys(t *testing.T) {
	tests := map[string]string{
		"latest lsi":      LatestLSIKey(),
		"dashboard":       DashboardCurrentKey(true, false, true),
		"snapshot":        ModulesSnapshotKey("latest"),
		"module signals":  ModuleSignalsKey("M1_RESERVES", "2024-01-01", "2024-01-31"),
		"lsi history":     LSIHistoryKey("2024-01-01", "2024-01-31", 100, 0),
		"job status":      JobStatusKey("job-1"),
		"recalc lock key": RecalculationLockKey(),
	}

	for name, value := range tests {
		if value == "" {
			t.Fatalf("%s key is empty", name)
		}
		if value[:12] != "ru-liquidity" {
			t.Fatalf("%s key has wrong prefix: %s", name, value)
		}
	}
}
