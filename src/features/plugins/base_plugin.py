from abc import ABC, abstractmethod
import pandas as pd

class BaseFeaturePlugin(ABC):
    """
    Abstract base class for drop-in feature engineering plugins.
    Any new plugin placed in the /features/plugins directory must inherit from this.
    """

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Name of the plugin (used for column prefixes or logging)."""
        pass

    @property
    @abstractmethod
    def required_columns(self) -> list[str]:
        """List of columns required from the base dataframe (e.g., ['close', 'volume'])."""
        pass

    @abstractmethod
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies the feature logic to a DataFrame representing a single ticker's history.
        Must return a DataFrame with the new feature columns added.
        """
        pass
