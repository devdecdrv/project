from fastapi import APIRouter, HTTPException, Depends
import asyncpg
from models.database import get_pool

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("/")
async def list_batches(pool: asyncpg.Pool = Depends(get_pool)):
    rows = await pool.fetch("SELECT * FROM batches ORDER BY created_at DESC")
    return [dict(r) for r in rows]


@router.get("/{batch_id}/topics")
async def get_topics(batch_id: str, pool: asyncpg.Pool = Depends(get_pool)):
    """All topics for a batch, ordered."""
    rows = await pool.fetch(
        "SELECT * FROM topics WHERE batch_id = $1 ORDER BY sort_order ASC",
        batch_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Batch not found or has no topics")
    return [dict(r) for r in rows]


@router.get("/{batch_id}")
async def get_batch(batch_id: str, pool: asyncpg.Pool = Depends(get_pool)):
    row = await pool.fetchrow("SELECT * FROM batches WHERE id = $1", batch_id)
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")
    return dict(row)
