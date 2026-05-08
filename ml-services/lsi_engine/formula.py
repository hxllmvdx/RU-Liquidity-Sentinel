def calculate_base_lsi(module_scores):
    if not module_scores:
        return 0.0
    return float(sum(module_scores.values()) / len(module_scores))
