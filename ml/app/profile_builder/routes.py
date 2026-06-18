import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .service import ProfileService
from .models import UnifiedProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profiles", tags=["profiles"])

# Global service instance (initialized at startup)
_service: Optional[ProfileService] = None


def init_profile_service(service: ProfileService):
    """Initialize the global profile service."""
    global _service
    _service = service
    logger.info("Profile service initialized")


def get_service() -> ProfileService:
    """Get the profile service instance."""
    if _service is None:
        raise RuntimeError("Profile service not initialized")
    return _service


class UpsertProfileRequest(BaseModel):
    """Request to upsert a profile."""
    agency_name: str
    record: Dict[str, Any]
    patient_id: Optional[str] = None


class UpsertProfileResponse(BaseModel):
    """Response after upserting a profile."""
    patient_id: str
    created: bool
    updated: bool


@router.post("", response_model=UpsertProfileResponse)
async def upsert_profile(request: UpsertProfileRequest) -> Dict[str, Any]:
    """
    Upsert (insert or update) a patient profile.

    Takes normalized data from adapter and stores unified profile.

    **Strategy:** Latest agency data wins (simple merge).

    **Returns:**
    - patient_id: Unique patient ID
    - created: True if new profile was created
    - updated: True if existing profile was updated
    """
    try:
        service = get_service()
        result = await service.upsert_profile(
            agency_name=request.agency_name,
            normalized_record=request.record,
            patient_id=request.patient_id
        )
        return result
    except Exception as e:
        logger.error(f"Error upserting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}", response_model=UnifiedProfile)
async def get_profile(patient_id: str) -> UnifiedProfile:
    """
    Retrieve a unified patient profile by ID.

    Used by Turn Orchestrator + Voice Gateway to get patient context.

    **Returns:** UnifiedProfile with all merged agency data.
    """
    try:
        service = get_service()
        profile = await service.get_profile(patient_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile not found: {patient_id}")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving profile {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list)
async def list_profiles(skip: int = 0, limit: int = 100):
    """
    List all patient profiles with pagination.

    **Query params:**
    - skip: Number of profiles to skip (default: 0)
    - limit: Number of profiles to return (default: 100, max: 1000)

    **Returns:** List of UnifiedProfile objects.
    """
    try:
        if limit > 1000:
            limit = 1000
        service = get_service()
        profiles = await service.list_profiles(skip=skip, limit=limit)
        return profiles
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/ready", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Check if profile service is ready."""
    try:
        service = get_service()
        if service.health_check():
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="MongoDB not available")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
