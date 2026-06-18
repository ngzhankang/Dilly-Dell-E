from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UnifiedProfile(BaseModel):
    """Unified patient profile across all agencies."""

    # Core identifiers
    patient_id: str = Field(..., description="Unique patient ID")

    # Demographics
    name: str
    dob: Optional[str] = None
    age: Optional[int] = None
    contact: Optional[str] = None

    # Assessment/Health
    emotion: Optional[str] = None
    problem_classes: List[str] = Field(default_factory=list)
    special_case: Optional[str] = None

    # Metadata
    agency_imports: Dict[str, Any] = Field(
        default_factory=dict,
        description="Last import from each agency"
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "pat_001",
                "name": "John Doe",
                "dob": "1950-06-15",
                "age": 75,
                "contact": "91234567",
                "emotion": "neutral",
                "problem_classes": ["Dementia", "Hypertension"],
                "special_case": "High fall risk",
                "agency_imports": {
                    "Care Corner": {"import_date": "2026-06-18", "records": 1},
                    "AIC": {"import_date": "2026-06-17", "records": 1}
                },
                "last_updated": "2026-06-18T12:00:00Z",
                "created_at": "2026-06-17T10:30:00Z"
            }
        }
