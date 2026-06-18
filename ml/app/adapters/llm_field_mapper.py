import json
import logging
from typing import Dict, Any, List
from ..llm.base import LLMClient

logger = logging.getLogger(__name__)

UNIFIED_SCHEMA_FIELDS = [
    "name",
    "dob",
    "age",
    "contact",
    "emotion",
    "problem_classes",
    "special_case",
]

MAPPING_SYSTEM_PROMPT = """You are a healthcare data integration specialist.

Your task is to map raw fields from an agency's form to our unified patient assessment schema.

You must understand that different agencies use different naming conventions and terminology to describe the same concepts:
- "date_of_birth", "DOB", "birth_date", "yob" all refer to: "dob"
- "patient_name", "fullname", "name", "pt_name" all refer to: "name"
- "diagnosis", "diagnosis_code", "condition", "icd_code" might refer to: "problem_classes"
- "mood", "emotional_state", "affect" refer to: "emotion"

There may also be instances where in the agency's form, a list of codes mapped to their respective options are given. (i.e. 1=Never married, 2=Married, etc.) In such cases, you should map the field to the appropriate unified schema field and note that the value is a code that needs to be interpreted.

Available target fields in our unified schema:
- name (patient name)
- dob (date of birth, format: YYYY-MM-DD)
- age (age in years)
- contact (phone/email)
- emotion (emotional state: happy, neutral, worried, confused)
- problem_classes (list of diagnoses/conditions/problem codes)
- special_case (red flags, urgent notes, warnings)

Respond ONLY with valid JSON:
{
  "mappings": {
    "source_field_name": "target_field_name",
    "another_source_field": "target_field_name_or_null"
  },
  "confidence": 0.85,
  "unmapped_fields": ["field1", "field2"],
  "notes": "Brief explanation of any ambiguous mappings"
}

If a source field doesn't map to any unified field, set its mapping to null.
Confidence is 0.0-1.0 representing how sure you are about the overall mapping quality.
"""


class LLMFieldMapper:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def map_fields(
        self, agency_name: str, raw_fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map agency fields to unified schema using LLM."""
        field_names = list(raw_fields.keys())

        prompt = f"""Agency: {agency_name}

Raw fields from their form:
{json.dumps(field_names, indent=2)}

First row of sample data (for context):
{json.dumps({k: str(v)[:50] if v else '' for k, v in list(raw_fields.items())[:7]}, indent=2)}

Please map these fields to our unified schema."""

        messages = [
            {"role": "system", "content": MAPPING_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        response = await self.llm_client.chat(messages)
        logger.info(f"LLM mapping response for {agency_name}: {response[:200]}...")

        try:
            # Handle markdown-formatted JSON responses (```json ... ```)
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]  # Remove ```json
            if json_str.startswith("```"):
                json_str = json_str[3:]  # Remove ```
            if json_str.endswith("```"):
                json_str = json_str[:-3]  # Remove trailing ```
            json_str = json_str.strip()

            mapping_result = json.loads(json_str)
            return mapping_result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            raise ValueError(
                f"LLM returned invalid JSON. Response: {response[:200]}"
            )

    def apply_mapping(
        self, records: List[Dict[str, Any]], mapping: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Apply field mapping to transform records to unified schema."""
        normalized_records = []

        for record in records:
            normalized = {}

            for source_field, target_field in mapping.get("mappings", {}).items():
                if target_field and source_field in record:
                    if target_field == "problem_classes":
                        value = record[source_field]
                        if isinstance(value, str) and value.strip():
                            normalized[target_field] = [value]
                        elif isinstance(value, list):
                            normalized[target_field] = value
                    else:
                        value = record[source_field]
                        if value not in (None, "", "nan"):
                            normalized[target_field] = str(value)

            normalized_records.append(normalized)

        return normalized_records
