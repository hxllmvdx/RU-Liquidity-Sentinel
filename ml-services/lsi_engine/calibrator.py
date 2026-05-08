def calibrate_lsi(raw_lsi):
    return max(0.0, min(100.0, raw_lsi))
