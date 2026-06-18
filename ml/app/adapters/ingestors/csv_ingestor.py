import pandas as pd
from typing import List, Dict, Any
from .base import Ingestor


class CSVIngestor(Ingestor):
    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse CSV or Excel file and return list of records."""
        try:
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)

            records = df.fillna('').to_dict('records')
            return records
        except Exception as e:
            raise ValueError(f"Failed to parse CSV/Excel file: {str(e)}")
