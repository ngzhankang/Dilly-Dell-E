import asyncio
import json
import tempfile
import pandas as pd
from pathlib import Path

from app.adapters.ingestors.csv_ingestor import CSVIngestor
from app.adapters.ingestors.json_ingestor import JSONIngestor


async def test_csv_ingestor():
    """Test CSV parsing."""
    print("\n=== Testing CSV Ingestor ===")

    csv_data = {
        "patient_name": ["John Doe", "Jane Smith"],
        "dob": ["1950-05-15", "1955-03-20"],
        "diagnosis_code": ["F03", "G30"],
        "mobility_status": ["bedridden", "assisted walking"],
    }
    df = pd.DataFrame(csv_data)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        csv_path = f.name

    ingestor = CSVIngestor()
    records = await ingestor.parse(csv_path)

    print(f"✓ Parsed {len(records)} records")
    print(f"  First record: {json.dumps(records[0], indent=2)}")

    Path(csv_path).unlink()
    return records


async def test_json_ingestor():
    """Test JSON parsing."""
    print("\n=== Testing JSON Ingestor ===")

    json_data = [
        {
            "pt_name": "John Doe",
            "birth_date": "1950-05-15",
            "condition": "Dementia",
            "contact_number": "98765432",
        },
        {
            "pt_name": "Jane Smith",
            "birth_date": "1955-03-20",
            "condition": "Parkinson's",
            "contact_number": "91234567",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(json_data, f)
        json_path = f.name

    ingestor = JSONIngestor()
    records = await ingestor.parse(json_path)

    print(f"✓ Parsed {len(records)} records")
    print(f"  First record: {json.dumps(records[0], indent=2)}")

    Path(json_path).unlink()
    return records


async def test_field_mapper_mock():
    """Test field mapping logic (without calling real LLM)."""
    print("\n=== Testing Field Mapping Logic ===")

    from app.adapters.llm_field_mapper import LLMFieldMapper

    raw_fields = {
        "patient_name": "John Doe",
        "dob": "1950-05-15",
        "diagnosis_code": "F03",
        "mobility_status": "bedridden",
    }

    mapping_result = {
        "mappings": {
            "patient_name": "name",
            "dob": "dob",
            "diagnosis_code": "problem_classes",
            "mobility_status": "special_case",
        },
        "confidence": 0.95,
        "unmapped_fields": [],
        "notes": "Diagnosis code mapped to problem_classes as F03 is ICD-10 dementia code",
    }

    records = [raw_fields, raw_fields]
    mapper = LLMFieldMapper(None)
    normalized = mapper.apply_mapping(records, mapping_result)

    print(f"✓ Applied mapping to {len(normalized)} records")
    print(f"  Mapping confidence: {mapping_result['confidence']}")
    print(f"  Normalized first record: {json.dumps(normalized[0], indent=2)}")

    return normalized


async def main():
    print("=" * 60)
    print("Agency Form Adapter — Test Suite")
    print("=" * 60)

    await test_csv_ingestor()
    await test_json_ingestor()
    await test_field_mapper_mock()

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
