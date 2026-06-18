import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from .models import UnifiedProfile

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing unified patient profiles."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "dilly_dell_e"):
        """Initialize profile service with MongoDB connection."""
        try:
            self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[db_name]
            self.profiles = self.db.unified_profiles

            # Create indexes
            self._create_indexes()
            logger.info(f"Connected to MongoDB: {db_name}")
        except ServerSelectionTimeoutError:
            logger.error(f"Failed to connect to MongoDB at {mongo_uri}")
            raise

    def _create_indexes(self):
        """Create MongoDB indexes for efficient queries."""
        try:
            self.profiles.create_index("patient_id", unique=True)
            self.profiles.create_index([("name", 1), ("dob", 1)])
            self.profiles.create_index("contact")
            logger.info("Indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    async def upsert_profile(
        self,
        agency_name: str,
        normalized_record: Dict[str, Any],
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert (insert or update) a patient profile.

        Simple strategy: latest agency data wins.

        Args:
            agency_name: Name of the agency sending data
            normalized_record: Normalized patient record from adapter
            patient_id: Optional explicit patient ID (generated if not provided)

        Returns:
            {
                "patient_id": str,
                "created": bool,
                "updated": bool
            }
        """
        try:
            # Generate patient_id if not provided
            if not patient_id:
                patient_id = f"pat_{self.profiles.count_documents({}):06d}"

            # Check if profile exists
            existing = self.profiles.find_one({"patient_id": patient_id})

            # Prepare profile data
            profile_data = {
                "patient_id": patient_id,
                "name": normalized_record.get("name"),
                "dob": normalized_record.get("dob"),
                "age": normalized_record.get("age"),
                "contact": normalized_record.get("contact"),
                "emotion": normalized_record.get("emotion"),
                "problem_classes": normalized_record.get("problem_classes", []),
                "special_case": normalized_record.get("special_case"),
                "last_updated": datetime.utcnow(),
            }

            # Add agency import metadata
            if existing:
                agency_imports = existing.get("agency_imports", {})
                created = False
            else:
                agency_imports = {}
                created = True
                profile_data["created_at"] = datetime.utcnow()

            # Update agency import record
            agency_imports[agency_name] = {
                "import_date": datetime.utcnow(),
                "record": normalized_record
            }
            profile_data["agency_imports"] = agency_imports

            # Upsert in MongoDB
            result = self.profiles.update_one(
                {"patient_id": patient_id},
                {"$set": profile_data},
                upsert=True
            )

            return {
                "patient_id": patient_id,
                "created": created,
                "updated": result.modified_count > 0
            }

        except Exception as e:
            logger.error(f"Error upserting profile: {e}")
            raise

    async def get_profile(self, patient_id: str) -> Optional[UnifiedProfile]:
        """
        Retrieve a unified profile by patient ID.

        Args:
            patient_id: Patient ID

        Returns:
            UnifiedProfile or None if not found
        """
        try:
            doc = self.profiles.find_one({"patient_id": patient_id})
            if not doc:
                return None

            # Remove MongoDB's _id field
            doc.pop("_id", None)

            return UnifiedProfile(**doc)

        except Exception as e:
            logger.error(f"Error retrieving profile {patient_id}: {e}")
            return None

    async def list_profiles(self, skip: int = 0, limit: int = 100) -> list:
        """
        List all profiles with pagination.

        Args:
            skip: Number of profiles to skip
            limit: Number of profiles to return

        Returns:
            List of UnifiedProfile objects
        """
        try:
            cursor = self.profiles.find().skip(skip).limit(limit)
            profiles = []
            for doc in cursor:
                doc.pop("_id", None)
                profiles.append(UnifiedProfile(**doc))
            return profiles

        except Exception as e:
            logger.error(f"Error listing profiles: {e}")
            return []

    def health_check(self) -> bool:
        """Check if MongoDB connection is healthy."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False
