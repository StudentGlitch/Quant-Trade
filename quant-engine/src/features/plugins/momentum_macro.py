import pandas as pd
from .base_plugin import BaseFeaturePlugin

class MomentumPlugin(BaseFeaturePlugin):
    @property
    def plugin_name(self) -> str:
        return "Simple_Momentum"

    @property
    def required_columns(self) -> list[str]:
        return ['adj_close']

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        df['plugin_mom_1m'] = df['adj_close'].pct_change(21) # ~1 month
        df['plugin_mom_3m'] = df['adj_close'].pct_change(63) # ~3 months
        return df
