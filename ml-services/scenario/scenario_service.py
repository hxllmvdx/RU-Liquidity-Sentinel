def run_scenario(shocks, baseline_lsi=0.0):
    return {"lsi": baseline_lsi + sum(shocks.values())}
