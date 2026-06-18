from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Ingestor(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a file and return list of records with raw fields."""
        pass
