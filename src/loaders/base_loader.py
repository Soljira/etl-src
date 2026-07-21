from abc import ABC, abstractmethod
import pandas as pd

class BaseLoader(ABC):
    """
    Abstract base class for data loaders.
    """
    
    @abstractmethod
    def load(self, df: pd.DataFrame, dataset_id: str) -> bool:
        """
        Loads the provided DataFrame into the target data store.
        If data for the dataset_id already exists, it should be replaced.
        Returns True if successful, False otherwise.
        """
        pass
