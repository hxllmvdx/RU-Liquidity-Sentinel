INSERT INTO backtest_results (period_name, start_date, end_date, peak_lsi, hit_rate, metrics)
VALUES ('demo_stress_period', '2022-02-20', '2022-03-20', 78.5, 0.82, '{"note":"demo seed"}')
ON CONFLICT DO NOTHING;
