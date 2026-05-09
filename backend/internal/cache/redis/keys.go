package redis

import "fmt"

const keyPrefix = "ru-liquidity"

func LatestLSIKey() string {
	return keyPrefix + ":lsi:latest"
}

func DashboardCurrentKey(includeShap, includeForecast, includeComment bool) string {
	return fmt.Sprintf("%s:dashboard:current:shap:%t:forecast:%t:comment:%t", keyPrefix, includeShap, includeForecast, includeComment)
}

func DashboardCurrentPattern() string {
	return keyPrefix + ":dashboard:current:*"
}

func ModulesSnapshotKey(date string) string {
	if date == "" {
		date = "latest"
	}
	return fmt.Sprintf("%s:modules:snapshot:%s", keyPrefix, date)
}

func ModulesSnapshotPattern() string {
	return keyPrefix + ":modules:snapshot:*"
}

func ModuleSignalsKey(moduleID, from, to string) string {
	return fmt.Sprintf("%s:modules:%s:signals:%s:%s", keyPrefix, moduleID, from, to)
}

func ModuleSignalsPattern() string {
	return keyPrefix + ":modules:*:signals:*"
}

func BacktestKey(episode, from, to string, includeShap, includeModuleBreakdown bool) string {
	return fmt.Sprintf("%s:backtest:%s:%s:%s:shap:%t:breakdown:%t", keyPrefix, episode, from, to, includeShap, includeModuleBreakdown)
}

func LSIHistoryKey(from, to string, limit, offset int) string {
	return fmt.Sprintf("%s:lsi:history:%s:%s:%d:%d", keyPrefix, from, to, limit, offset)
}

func JobStatusKey(jobID string) string {
	return fmt.Sprintf("%s:job:%s:status", keyPrefix, jobID)
}

func RecalculationLockKey() string {
	return keyPrefix + ":lock:recalculation"
}
