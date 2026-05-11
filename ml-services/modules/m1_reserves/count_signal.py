import pandas as pd
import numpy as np
from scipy.stats import median_abs_deviation



class M1CountSignals():
    def __init__(self, df_all: pd.DataFrame):
        self.df_all = df_all
    
    def mad_score_ruonia(self):
        df= pd.DataFrame()
        df["ruonia_mediana_day"] = self.df_all["ruonia"].rolling(window=1095, min_periods=365).median()
        df["ruonia_mad_day"] = self.df_all["ruonia"].rolling(window=1095, min_periods=365).apply(lambda x: median_abs_deviation(x, nan_policy='omit'))
        self.df_all["mad_score_ruonia"] =(self.df_all["ruonia"] - df["ruonia_mediana_day"]) / df["ruonia_mad_day"]

    def mad_score_spread(self):
        df = pd.DataFrame()
        df['spread_median'] = self.df_all["spread"].rolling(window=1095, min_periods=365).median()
        df['spread_mad'] = self.df_all["spread"].rolling(window=1095, min_periods=365).apply(lambda x: median_abs_deviation(x, nan_policy='omit'))
        self.df_all['mad_score_spread'] = (self.df_all["spread"] - df['spread_median']) / df['spread_mad']



