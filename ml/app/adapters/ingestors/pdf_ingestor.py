import logging
from typing import List, Dict, Any

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from .base import Ingestor

logger = logging.getLogger(__name__)


class PDFFormIngestor(Ingestor):
    """Extract data from fillable PDF forms (AcroForm only)."""

    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a fillable PDF form and extract field data.

        Supports:
        - Filled text fields
        - Ticked checkboxes
        - Radio buttons and dropdowns

        Note: Only works with fillable PDFs (AcroForm).
        Scanned/handwritten PDFs are not supported.
        """
        try:
            form_data = self._extract_form_fields(file_path)

            if not form_data:
                raise ValueError(
                    "No form fields found in PDF. "
                    "This PDF may be a scanned image rather than a fillable form."
                )

            logger.info(f"Extracted {len(form_data)} form fields from PDF")
            return [form_data]

        except Exception as e:
            raise ValueError(f"Failed to parse PDF form: {str(e)}")

    def _extract_form_fields(self, file_path: str) -> Dict[str, Any]:
        """
        Extract AcroForm fields from fillable PDF.

        Handles:
        - Text input fields
        - Checkbox values
        - Radio button selections
        - Dropdown values
        """
        form_data = {}

        if not PyPDF2:
            raise ImportError(
                "PyPDF2 is required for PDF form extraction. "
                "Install with: pip install PyPDF2"
            )

        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)

                # Check if PDF has form fields
                if "/AcroForm" not in reader.trailer["/Root"]:
                    return {}

                # Extract form field values
                for page in reader.pages:
                    if "/Annots" not in page:
                        continue

                    for annot_ref in page["/Annots"]:
                        annot = annot_ref.get_object()

                        if "/T" in annot:  # Field name
                            field_name = str(annot["/T"]).strip("()")

                            # Extract field value based on type
                            if "/V" in annot:  # Regular value
                                form_data[field_name] = str(annot["/V"]).strip("()")
                            elif "/AS" in annot:  # Appearance state (for checkboxes)
                                # "/Off" means unchecked, anything else means checked
                                is_checked = str(annot["/AS"]) != "/Off"
                                form_data[field_name] = "Yes" if is_checked else "No"

        except Exception as e:
            logger.warning(f"Error extracting AcroForm fields: {e}")

        return form_data


class PDFInterRAIIngestor(PDFFormIngestor):
    """
    Specialized ingestor for interRAI assessment forms.

    Maps extracted PDF fields directly to interRAI assessment structure.
    """

    # Mapping of common interRAI field patterns to unified schema fields
    INTERRAI_FIELD_MAPPING = {
        # Demographics
        "patient.*name": "name",
        "client.*name": "name",
        "full.*name": "name",
        "date.*birth": "dob",
        "birth.*date": "dob",
        "d.o.b": "dob",
        "age": "age",
        "phone": "contact",
        "contact": "contact",
        # Cognitive
        "cognitive.*status": "cognition",
        "mental.*status": "cognition",
        "mmse": "cognition",
        # Mood/Emotion
        "mood": "emotion",
        "emotional.*state": "emotion",
        "affect": "emotion",
        # Diagnoses
        "diagnosis": "problem_classes",
        "condition": "problem_classes",
        "icd": "problem_classes",
        # Functional status - these become special_case flags
        "fall.*risk": "special_case",
        "pressure.*ulcer": "special_case",
        "mobility": "special_case",
        "adl": "special_case",
    }

    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse interRAI form and map to unified schema.
        """
        raw_records = await super().parse(file_path)
        normalized_records = []

        for record in raw_records:
            normalized = self._map_interrai_fields(record)
            normalized_records.append(normalized)

        return normalized_records

    def _map_interrai_fields(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map raw interRAI form fields to unified schema.
        """
        import re

        normalized = {}

        for raw_field, raw_value in raw_record.items():
            if not isinstance(raw_value, str) or not raw_value.strip():
                continue

            # Try to find matching unified schema field
            for pattern, unified_field in self.INTERRAI_FIELD_MAPPING.items():
                if re.search(pattern, raw_field, re.IGNORECASE):
                    # Special handling for different field types
                    if unified_field == "problem_classes":
                        if unified_field not in normalized:
                            normalized[unified_field] = []
                        if raw_value.strip():
                            normalized[unified_field].append(raw_value)
                    elif unified_field == "special_case":
                        # Accumulate special cases/flags
                        if unified_field not in normalized:
                            normalized[unified_field] = []
                        normalized[unified_field].append(f"{raw_field}: {raw_value}")
                    else:
                        normalized[unified_field] = raw_value
                    break

        # Clean up accumulated lists
        if "problem_classes" in normalized and isinstance(normalized["problem_classes"], list):
            normalized["problem_classes"] = [
                p for p in normalized["problem_classes"] if p
            ]
        if "special_case" in normalized and isinstance(normalized["special_case"], list):
            normalized["special_case"] = "; ".join(normalized["special_case"])

        return normalized
