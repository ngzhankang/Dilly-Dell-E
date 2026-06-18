import logging
import tempfile
from typing import Dict, Any, List
from .ingestors.csv_ingestor import CSVIngestor
from .ingestors.json_ingestor import JSONIngestor
from .llm_field_mapper import LLMFieldMapper
from ..llm.base import LLMClient

logger = logging.getLogger(__name__)


class AdapterMapper:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.field_mapper = LLMFieldMapper(llm_client)
        self.csv_ingestor = CSVIngestor()
        self.json_ingestor = JSONIngestor()

    async def import_agency_data(
        self, file_path: str, agency_name: str, file_format: str
    ) -> Dict[str, Any]:
        """
        End-to-end import: parse file → map fields → normalize data.

        Returns:
            {
                "success": bool,
                "records_normalized": int,
                "mapping_confidence": float,
                "records": [...],
                "mapping_metadata": {...}
            }
        """
        try:
            logger.info(
                f"Starting import for {agency_name} (format: {file_format})"
            )

            ingestor = self._get_ingestor(file_format)
            raw_records = await ingestor.parse(file_path)
            logger.info(f"Parsed {len(raw_records)} records from {agency_name}")

            if not raw_records:
                return {
                    "success": False,
                    "error": "No records found in file",
                }

            first_record = raw_records[0]
            mapping_result = await self.field_mapper.map_fields(
                agency_name, first_record
            )
            logger.info(
                f"Field mapping confidence: {mapping_result.get('confidence', 0)}"
            )

            mappings = mapping_result.get("mappings", {})
            normalized_records = self.field_mapper.apply_mapping(
                raw_records, {"mappings": mappings}
            )

            return {
                "success": True,
                "agency": agency_name,
                "records_normalized": len(normalized_records),
                "mapping_confidence": mapping_result.get("confidence", 0.0),
                "unmapped_fields": mapping_result.get("unmapped_fields", []),
                "mapping_notes": mapping_result.get("notes", ""),
                "records": normalized_records,
                "mapping_metadata": {
                    "source_to_target": mappings,
                    "confidence": mapping_result.get("confidence", 0.0),
                    "unmapped": mapping_result.get("unmapped_fields", []),
                },
            }

        except Exception as e:
            logger.error(f"Import failed for {agency_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "agency": agency_name,
            }

    def _get_ingestor(self, file_format: str):
        """Get appropriate ingestor for file format."""
        if file_format.lower() in ["csv", "xlsx", "xls"]:
            return self.csv_ingestor
        elif file_format.lower() == "json":
            return self.json_ingestor
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
