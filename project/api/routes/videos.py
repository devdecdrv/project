from fastapi import APIRouter, HTTPException, Depends
import asyncpg
from models.database import get_pool

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/")
async def list_videos(
    batch_id: str | None = None,
    topic_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    pool: asyncpg.Pool = Depends(get_pool),
):
    """List videos, optionally filtered by batch or topic."""
    conditions = []
    args = []

    if batch_id:
        args.append(batch_id)
        conditions.append(f"v.batch_id = ${len(args)}")
    if topic_id:
        args.append(topic_id)
        conditions.append(f"v.topic_id = ${len(args)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    args += [limit, offset]

    rows = await pool.fetch(
        f"""
        SELECT v.id, v.title, v.thumbnail_url, v.duration_secs,
               v.batch_id, v.topic_id, v.video_type,
               t.name AS topic_name, b.name AS batch_name
        FROM videos v
        LEFT JOIN topics t ON t.id = v.topic_id
        LEFT JOIN batches b ON b.id = v.batch_id
        {where}
        ORDER BY v.scraped_at DESC
        LIMIT ${len(args)-1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows]


@router.get("/{video_id}")
async def get_video(video_id: str, pool: asyncpg.Pool = Depends(get_pool)):
    """Single video — includes pw_url so proxy can use it."""
    row = await pool.fetchrow(
        """
        SELECT v.*, t.name AS topic_name, b.name AS batch_name
        FROM videos v
        LEFT JOIN topics t ON t.id = v.topic_id
        LEFT JOIN batches b ON b.id = v.batch_id
        WHERE v.id = $1
        """,
        video_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Video not found")
    return dict(row)
