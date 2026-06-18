import logging
from typing import List, Dict, Any, Tuple
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    PaddleOCR = None
    logger.warning("paddleocr not installed - OCR features disabled")

try:
    from PIL import Image
    import numpy as np
except ImportError:
    Image = None
    np = None

from .base import Ingestor

logger = logging.getLogger(__name__)


class PDFFormIngestor(Ingestor):
    """Extract data from filled PDF forms (checkboxes, text fields, handwriting)."""

    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a filled PDF form and extract field data.

        Supports:
        - Filled text fields
        - Ticked checkboxes
        - Handwritten text (via OCR)
        - Radio buttons and dropdowns
        """
        if not pdfplumber:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install with: pip install pdfplumber"
            )

        try:
            records = []

            with pdfplumber.open(file_path) as pdf:
                # Extract form fields (acroform if available)
                form_data = self._extract_form_fields(file_path, pdf)

                if form_data:
                    # If PDF has form fields (AcroForm), use those
                    logger.info(f"Extracted {len(form_data)} form fields from PDF")
                    records.append(form_data)
                else:
                    # Fallback: OCR-based extraction
                    logger.info(
                        "No form fields found, attempting OCR-based extraction..."
                    )
                    for page_num, page in enumerate(pdf.pages):
                        page_data = await self._extract_page_with_ocr(
                            page, page_num
                        )
                        if page_data:
                            records.append(page_data)

            if not records:
                raise ValueError("No data could be extracted from PDF")

            return records

        except Exception as e:
            raise ValueError(f"Failed to parse PDF form: {str(e)}")

    def _extract_form_fields(self, file_path: str, pdf) -> Dict[str, Any]:
        """
        Extract AcroForm fields from PDF if they exist.

        This handles:
        - Text input fields
        - Checkbox values
        - Radio button selections
        - Dropdown values
        """
        form_data = {}

        try:
            if not PyPDF2:
                logger.warning(
                    "PyPDF2 not installed, skipping AcroForm extraction"
                )
                return {}

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
            return {}

        return form_data if form_data else {}

    async def _extract_page_with_ocr(
        self, page, page_num: int
    ) -> Dict[str, Any]:
        """
        Extract text from page using PaddleOCR.

        PaddleOCR is better for:
        - Handwritten text in form fields
        - Text in boxes
        - Multi-language support (English, Mandarin, Malay, Tamil)
        - No external binary required
        """
        page_data = {}

        if not PADDLEOCR_AVAILABLE:
            logger.error(
                "PaddleOCR not available. Install with: "
                "pip install paddleocr"
            )
            return {}

        try:
            # Convert page to image
            image = page.to_image()
            pil_image = image.original

            # Convert PIL Image to numpy array (PaddleOCR requires numpy array or file path)
            img_array = np.array(pil_image)

            # Initialize PaddleOCR (auto-downloads model on first run)
            # use_angle_cls=True handles rotated text detection
            # Supports: English, Chinese, Japanese, Korean, etc.
            ocr = PaddleOCR(use_angle_cls=True, lang='en')

            # Run OCR - returns list of [[[x,y], [x,y], [x,y], [x,y]], 'text', confidence]
            result = ocr.ocr(img_array)

            if not result or not result[0]:
                logger.warning(f"PaddleOCR returned no results for page {page_num}")
                return {}

            # Extract text and group by position (vertical grouping for form fields)
            fields = self._group_paddle_results_by_position(result[0])

            # Collect all text as fallback
            all_text = []
            for line in result[0]:
                if line and line[0]:  # text exists
                    all_text.append(line[0])

            # Add fields to page data
            for field_name, field_value in fields.items():
                page_data[field_name] = field_value

            # Add raw text as fallback
            if all_text:
                page_data["page_text"] = " ".join(all_text)

            page_data["page_number"] = page_num + 1

            logger.info(f"PaddleOCR extracted {len(fields)} fields from page {page_num + 1}")

        except Exception as e:
            logger.error(f"Error during PaddleOCR extraction on page {page_num}: {e}")

        return page_data if page_data else {}

    def _group_text_by_position(self, ocr_data: Dict) -> Dict[str, str]:
        """
        Group OCR text by vertical position to identify form fields.

        Text on the same horizontal line is grouped together as one field.
        """
        fields = {}
        current_field = []
        current_y = None
        y_threshold = 10  # pixels - consider text on same line if within threshold

        for i, text in enumerate(ocr_data.get("text", [])):
            if not text.strip():
                continue

            y = ocr_data.get("top", [0])[i]

            # Check if this text is on the same line as previous
            if current_y is None or abs(y - current_y) <= y_threshold:
                current_field.append(text)
                current_y = y
            else:
                # New field detected
                if current_field:
                    field_value = " ".join(current_field)
                    field_name = f"field_{len(fields)}"
                    fields[field_name] = field_value

                current_field = [text]
                current_y = y

        # Add last field
        if current_field:
            field_value = " ".join(current_field)
            field_name = f"field_{len(fields)}"
            fields[field_name] = field_value

        return fields

    def _group_paddle_results_by_position(self, paddle_results: List) -> Dict[str, str]:
        """
        Group PaddleOCR results by vertical position to identify form fields.

        PaddleOCR returns: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], 'text', confidence]

        Text on the same horizontal line is grouped together as one field.
        """
        fields = {}
        current_field = []
        current_y = None
        y_threshold = 15  # pixels - consider text on same line if within threshold

        for item in paddle_results:
            if not item or len(item) < 2:
                continue

            text = item[1]  # Text content
            confidence = item[2] if len(item) > 2 else 0.0

            if not text or not text.strip():
                continue

            # Convert confidence to float and filter low confidence
            try:
                confidence = float(confidence)
                if confidence < 0.3:
                    continue
            except (ValueError, TypeError):
                # If confidence conversion fails, include anyway
                pass

            # Get Y coordinate from bounding box (top-left Y)
            bbox = item[0]  # List of [x, y] coordinates
            if bbox and len(bbox) > 0:
                try:
                    y = float(bbox[0][1])  # Y coordinate of first point (ensure it's float)
                except (ValueError, TypeError, IndexError):
                    y = 0.0
            else:
                y = 0.0

            # Group text on same horizontal line
            if current_y is None or abs(y - current_y) <= y_threshold:
                current_field.append(text.strip())
                current_y = y
            else:
                # New field detected
                if current_field:
                    field_value = " ".join(current_field)
                    field_name = f"field_{len(fields)}"
                    fields[field_name] = field_value

                current_field = [text.strip()]
                current_y = y

        # Add last field
        if current_field:
            field_value = " ".join(current_field)
            field_name = f"field_{len(fields)}"
            fields[field_name] = field_value

        return fields

    def _detect_checkbox_status(self, image: Image.Image, x: int, y: int, w: int, h: int) -> bool:
        """
        Detect if a checkbox at given coordinates is ticked.

        Looks for:
        - Black marks (pen strokes)
        - Filled regions
        - Checkmark patterns
        """
        try:
            # Crop checkbox region
            bbox = (x, y, x + w, y + h)
            checkbox_img = image.crop(bbox)

            # Convert to grayscale
            checkbox_gray = checkbox_img.convert("L")

            # Count dark pixels (filled/marked)
            pixels = list(checkbox_gray.getdata())
            dark_pixel_count = sum(1 for p in pixels if p < 128)

            # If > 30% of pixels are dark, checkbox is likely marked
            threshold = len(pixels) * 0.3
            return dark_pixel_count > threshold

        except Exception as e:
            logger.warning(f"Error detecting checkbox status: {e}")
            return False


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
