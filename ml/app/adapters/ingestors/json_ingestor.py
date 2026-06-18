import json
from typing import List, Dict, Any
from .base import Ingestor


class JSONIngestor(Ingestor):
    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse JSON file and return list of records."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            else:
                raise ValueError("JSON must be an object or array of objects")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON file: {str(e)}")
