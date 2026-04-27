import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.live import LiveChannelDiagnosisRead, LiveChannelGroupRead, LiveChannelRead, LiveChannelUpdate
from app.services import live_m3u

router = APIRouter(prefix="/live", tags=["live"])


@router.get("/groups", response_model=list[LiveChannelGroupRead])
async def list_groups(db: AsyncSession = Depends(get_db)) -> list:
    return await live_m3u.list_groups(db)


@router.get("/channels", response_model=list[LiveChannelRead])
async def list_channels(
    group_id: uuid.UUID | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list:
    return await live_m3u.list_channels(db, group_id=group_id, q=q)


@router.patch("/channels/{channel_id}", response_model=LiveChannelRead)
async def update_channel(
    channel_id: uuid.UUID,
    payload: LiveChannelUpdate,
    db: AsyncSession = Depends(get_db),
) -> object:
    return await live_m3u.update_channel_enabled(db, channel_id, payload.enabled)


@router.post("/channels/{channel_id}/diagnose", response_model=LiveChannelDiagnosisRead)
async def diagnose_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> object:
    return await live_m3u.diagnose_channel(db, channel_id)
