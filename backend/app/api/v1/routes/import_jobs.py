import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.import_job import ImportJobRead
from app.services import import_jobs

router = APIRouter(prefix="/import-jobs", tags=["import-jobs"])


@router.get("", response_model=list[ImportJobRead])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[ImportJobRead]:
    return await import_jobs.list_import_jobs(db)


@router.get("/{job_id}", response_model=ImportJobRead)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ImportJobRead:
    return await import_jobs.get_import_job(db, job_id)
