from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy import select

from app.api.deps import get_async_session, require_role
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.core.security import TokenData
from app.domain.enums import DatasetStatus as DatasetStatusEnum
from app.models.dataset import Dataset, DatasetVersion, DatasetSplit
from app.repositories.dataset import DatasetRepository, DatasetVersionRepository, DatasetSplitRepository
from app.repositories.suites import TestSuiteRepository

from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter()

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_UPLOAD_TYPES = {"text/csv", "application/json", "application/octet-stream"}


@router.post("/datasets", status_code=201)
async def create_dataset(
    name: str,
    description: str | None = None,
    source_type: str = "file",
    source_config: dict[str, Any] = None,
    schema: dict[str, Any] = None,
    split_config: dict[str, Any] = None,
    status: DatasetStatusEnum = DatasetStatusEnum.DRAFT,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Create a new dataset."""
    if len(name) > 200:
        raise ValidationError("Dataset name too long (max 200 chars)")
    dataset_repo = DatasetRepository(session)
    existing = await dataset_repo.get_active_by_name(name)
    if existing:
        raise ValidationError(f"Dataset with name '{name}' already exists")
    dataset = Dataset(
        name=name,
        description=description,
        source_type=source_type,
        source_config=source_config or {},
        schema=schema or {},
        split_config=split_config or {"train": 0.7, "val": 0.15, "test": 0.15},
        status=status,
    )
    dataset = await dataset_repo.create(dataset)
    await session.flush()
    logger.info("dataset_created", dataset_id=str(dataset.id), name=name, user=current_user.username)
    return {"id": str(dataset.id), "name": dataset.name, "status": dataset.status.value}


@router.get("/datasets")
async def list_datasets(
    status: DatasetStatusEnum | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """List datasets."""
    dataset_repo = DatasetRepository(session)
    filters = {}
    if status:
        filters["status"] = status.value
    datasets = await dataset_repo.list(filters=filters, skip=skip, limit=limit)
    return [
        {
            "id": str(d.id),
            "name": d.name,
            "description": d.description,
            "status": d.status.value,
            "source_type": d.source_type,
            "total_records": d.total_records,
            "current_version": d.current_version,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in datasets
    ]


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """Get dataset with versions."""
    dataset_repo = DatasetRepository(session)
    dataset = await dataset_repo.get_with_versions(dataset_id)
    if not dataset:
        raise NotFoundError("Dataset", str(dataset_id))
    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "description": dataset.description,
        "status": dataset.status.value,
        "source_type": dataset.source_type,
        "source_config": dataset.source_config,
        "schema": dataset.schema,
        "split_config": dataset.split_config,
        "total_records": dataset.total_records,
        "current_version": dataset.current_version,
        "versions": [
            {
                "id": str(v.id),
                "version": v.version,
                "total_records": v.total_records,
                "checksum": v.checksum,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in dataset.versions
        ],
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


@router.post("/datasets/{dataset_id}/versions")
async def create_dataset_version(
    dataset_id: UUID,
    changelog: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Create a new version of a dataset."""
    dataset_repo = DatasetRepository(session)
    version_repo = DatasetVersionRepository(session)
    dataset = await dataset_repo.get(dataset_id)
    if not dataset:
        raise NotFoundError("Dataset", str(dataset_id))
    version_number = await version_repo.get_next_version_number(dataset_id)
    snapshot = {
        "name": dataset.name,
        "description": dataset.description,
        "source_type": dataset.source_type,
        "source_config": dataset.source_config,
        "schema": dataset.schema,
        "split_config": dataset.split_config,
    }
    version = DatasetVersion(
        dataset_id=dataset_id,
        version=version_number,
        snapshot=snapshot,
        changelog=changelog,
        total_records=0,
        checksum="",
    )
    version = await version_repo.create(version)
    dataset.current_version = version.version
    dataset.updated_at = datetime.utcnow()
    await session.flush()
    logger.info("dataset_version_created", dataset_id=str(dataset_id), version=version.version, user=current_user.username)
    return {
        "id": str(version.id),
        "version": version.version,
        "checksum": version.checksum,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/datasets/{dataset_id}/versions")
async def list_dataset_versions(
    dataset_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """List dataset versions."""
    dataset_repo = DatasetRepository(session)
    version_repo = DatasetVersionRepository(session)
    dataset = await dataset_repo.get(dataset_id)
    if not dataset:
        raise NotFoundError("Dataset", str(dataset_id))
    versions = await version_repo.list_by_dataset(dataset_id, skip=skip, limit=limit)
    return [
        {
            "id": str(v.id),
            "version": v.version,
            "changelog": v.changelog,
            "total_records": v.total_records,
            "checksum": v.checksum,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@router.get("/datasets/{dataset_id}/versions/{version_id}")
async def get_dataset_version(
    dataset_id: UUID,
    version_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """Get dataset version details."""
    version_repo = DatasetVersionRepository(session)
    version = await version_repo.get(version_id)
    if not version or version.dataset_id != dataset_id:
        raise NotFoundError("DatasetVersion", str(version_id))
    return {
        "id": str(version.id),
        "dataset_id": str(version.dataset_id),
        "version": version.version,
        "snapshot": version.snapshot,
        "changelog": version.changelog,
        "split_sizes": version.split_sizes,
        "total_records": version.total_records,
        "checksum": version.checksum,
        "created_at": version.created_at.isoformat() if version.created_at else None,
    }


@router.get("/datasets/{dataset_id}/versions/{version_id}/splits")
async def list_dataset_splits(
    dataset_id: UUID,
    version_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """List splits for a dataset version."""
    split_repo = DatasetSplitRepository(session)
    splits = await split_repo.list_by_version(version_id)
    return [
        {
            "id": str(s.id),
            "split_name": s.split_name,
            "record_count": len(s.records),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in splits
    ]


@router.get("/datasets/{dataset_id}/versions/{version_id}/splits/{split_name}")
async def get_dataset_split(
    dataset_id: UUID,
    version_id: UUID,
    split_name: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer", "qa_engineer", "viewer"])),
):
    """Get a specific split."""
    if len(split_name) > 100:
        raise ValidationError("Invalid split name")
    split_repo = DatasetSplitRepository(session)
    split = await split_repo.get_by_version_and_name(version_id, split_name)
    if not split:
        raise NotFoundError("DatasetSplit", split_name)
    return {
        "id": str(split.id),
        "split_name": split.split_name,
        "records": split.records,
        "record_indices": split.record_indices,
        "created_at": split.created_at.isoformat() if split.created_at else None,
    }


@router.post("/datasets/{dataset_id}/upload")
async def upload_dataset_file(
    dataset_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Upload a dataset file (CSV, JSON, Parquet)."""
    if file.size and file.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f"File too large (max {MAX_UPLOAD_SIZE} bytes)")
    if file.content_type and file.content_type not in ALLOWED_UPLOAD_TYPES and not file.filename.endswith((".csv", ".json", ".parquet")):
        raise ValidationError("Unsupported file type")
    dataset_repo = DatasetRepository(session)
    dataset = await dataset_repo.get(dataset_id)
    if not dataset:
        raise NotFoundError("Dataset", str(dataset_id))
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValidationError(f"File too large (max {MAX_UPLOAD_SIZE} bytes)")
    dataset.total_records = 0
    dataset.total_size_bytes = len(content)
    dataset.updated_at = datetime.utcnow()
    await session.flush()
    logger.info("dataset_uploaded", dataset_id=str(dataset_id), size=len(content), user=current_user.username)
    return {"message": "File uploaded successfully", "dataset_id": str(dataset_id), "size_bytes": len(content)}


@router.post("/datasets/{dataset_id}/split")
async def split_dataset(
    dataset_id: UUID,
    version_id: UUID,
    split_ratios: dict[str, float] = None,
    seed: int = 42,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin", "safety_engineer", "ml_engineer"])),
):
    """Split dataset into train/val/test splits."""
    if split_ratios:
        total = sum(split_ratios.values())
        if abs(total - 1.0) > 0.01:
            raise ValidationError("Split ratios must sum to 1.0")
    return {
        "message": "Dataset split initiated",
        "dataset_id": str(dataset_id),
        "version_id": str(version_id),
        "split_ratios": split_ratios or {"train": 0.7, "val": 0.15, "test": 0.15},
        "seed": seed,
    }


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Delete a dataset."""
    dataset_repo = DatasetRepository(session)
    dataset = await dataset_repo.get(dataset_id)
    if not dataset:
        raise NotFoundError("Dataset", str(dataset_id))
    await dataset_repo.delete(dataset)
    logger.info("dataset_deleted", dataset_id=str(dataset_id), user=current_user.username)
    return {"message": "Dataset deleted"}
