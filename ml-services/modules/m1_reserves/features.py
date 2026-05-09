import pandas as pd

def build_features(observations: dict):

    df = pd.DataFrame(observations)
    df_actual = df[df['series_key'] == 'cbr_reserves_actual'].groupby('observation_date')['value_numeric'].mean().reset_index()
    df_required = df[df['series_key'] == 'cbr_reserves_required'].groupby('observation_date')['value_numeric'].mean().reset_index()
    df_ruonia = df[df['series_key'] == 'cbr_ruonia_daily'].groupby('observation_date')['value_numeric'].mean().reset_index()

    features = df_actual.rename(columns={'value_numeric': 'actual'})
    features = features.merge(df_required.rename(columns={'value_numeric': 'required'}), on='observation_date')
    features = features.merge(df_ruonia.rename(columns={'value_numeric': 'ruonia'}), on='observation_date')

    features['spread'] = features['actual'] - features['required']
    return {"module": "m1", "feature_count": len(observations)}
