def forecast_lsi(horizon_days=7):
    return [{"day": day, "lsi": 0.0} for day in range(1, horizon_days + 1)]
