import numpy as np
import pandas as pd

def mad_score(series, window=36):
    hist = series[:-1]
    if len(hist) < 12:
        return 0.0
    median = np.median(hist)
    mad = np.median(np.abs(hist - median))
    if mad == 0:
        return 0.0
    return 0.6745 * (series.iloc[-1] - median) / mad

def calculate_signal(features):
    if not features.get('features'):
        return {"module_id": "m1", "signal": 0.0, "status": "green"}
    
    df = pd.DataFrame(features['features'])
    df = df.sort_values('observation_date')
    
    spread_mad = mad_score(df['spread'])
    ruonia_mad = mad_score(df['ruonia'])
    
    overall_score = (spread_mad + ruonia_mad) / 2
    

    if overall_score > 2.5:
        status = "red"
    elif overall_score > 1.5:
        status = "yellow"
    else:
        status = "green"
    
    flag_end_of_period = False  
    
    return {
        "module_id": "m1",
        "signal": overall_score,
        "status": status,
        "raw_value": df['spread'].iloc[-1],
        "normalized_value": spread_mad,
        "flags": ["Flag_EndOfPeriod"] if flag_end_of_period else []
    }
