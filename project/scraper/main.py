"""
PW Scraper
----------
Fetches batch → topics → videos from PW's API and upserts into PostgreSQL.

Usage:
    python main.py --batch-id <batch_id>
    python main.py --batch-id <batch_id> --subject-id <subject_id>
"""

import asyncio
import os
import sys
from typing import Optional

import asyncpg
import httpx
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

console = Console()
app = typer.Typer()

PW_API_BASE = os.getenv("PW_API_BASE", "https://api.penpencil.co")
AUTH_TOKEN   = os.getenv("PW_AUTH_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Headers that PW's API expects
def pw_headers() -> dict:
    return {
        "Authorization":  f"Bearer {AUTH_TOKEN}",
        "Client-Id":      "5eb393ee95fab7468a79d189",
        "Client-Type":    "WEB",
        "User-Agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept":         "application/json",
    }


async def fetch_batch_info(client: httpx.AsyncClient, batch_id: str) -> dict:
    """Fetch batch metadata."""
    r = await client.get(
        f"{PW_API_BASE}/v3/batches/{batch_id}",
        headers=pw_headers(),
    )
    r.raise_for_status()
    return r.json().get("data", {})


async def fetch_subjects(client: httpx.AsyncClient, batch_id: str) -> list[dict]:
    """Fetch all subjects (topics containers) for a batch."""
    r = await client.get(
        f"{PW_API_BASE}/v3/batches/{batch_id}/subjects",
        headers=pw_headers(),
    )
    r.raise_for_status()
    return r.json().get("data", [])


async def fetch_topics(
    client: httpx.AsyncClient, batch_id: str, subject_id: str
) -> list[dict]:
    """Fetch topics for a subject within a batch."""
    r = await client.get(
        f"{PW_API_BASE}/v3/batches/{batch_id}/subjects/{subject_id}/topics",
        headers=pw_headers(),
    )
    r.raise_for_status()
    return r.json().get("data", [])


async def fetch_videos_for_topic(
    client: httpx.AsyncClient, batch_id: str, subject_id: str, topic_id: str
) -> list[dict]:
    """Fetch video list for a topic."""
    videos = []
    page = 1
    while True:
        r = await client.get(
            f"{PW_API_BASE}/v3/batches/{batch_id}/subjects/{subject_id}/topics/{topic_id}/contents",
            headers=pw_headers(),
            params={"page": page, "contentType": "videos"},
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("data", [])
        videos.extend(items)
        # PW paginates; stop when we get fewer than expected or an empty page
        if len(items) < 10 or not items:
            break
        page += 1
    return videos


async def fetch_video_url(
    client: httpx.AsyncClient, video_id: str, video_key: str
) -> Optional[str]:
    """
    Fetch the actual m3u8/mp4 stream URL for a video.
    PW returns a signed URL valid for a short window.
    """
    r = await client.get(
        f"{PW_API_BASE}/v3/videos/{video_id}",
        headers=pw_headers(),
        params={"videoKey": video_key},
    )
    if r.status_code != 200:
        return None
    data = r.json().get("data", {})
    # PW returns playerResponse.videoUrl or similar
    return (
        data.get("videoUrl")
        or data.get("playerResponse", {}).get("videoUrl")
        or data.get("url")
    )


async def upsert_batch(conn: asyncpg.Connection, batch: dict):
    await conn.execute(
        """
        INSERT INTO batches (id, name, subject, slug)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                subject = EXCLUDED.subject,
                slug = EXCLUDED.slug
        """,
        batch.get("_id") or batch.get("id"),
        batch.get("name", "Untitled Batch"),
        batch.get("subject", {}).get("name") if isinstance(batch.get("subject"), dict) else batch.get("subject"),
        batch.get("slug"),
    )


async def upsert_topic(conn: asyncpg.Connection, topic: dict, batch_id: str, order: int):
    await conn.execute(
        """
        INSERT INTO topics (id, batch_id, name, slug, sort_order)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO UPDATE
            SET name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                sort_order = EXCLUDED.sort_order
        """,
        topic.get("_id") or topic.get("id"),
        batch_id,
        topic.get("name", "Untitled Topic"),
        topic.get("slug"),
        order,
    )


async def upsert_video(
    conn: asyncpg.Connection,
    video: dict,
    batch_id: str,
    topic_id: str,
    subject_id: str,
    subject_slug: str,
    topic_slug: str,
    pw_url: Optional[str],
):
    vid_id = video.get("_id") or video.get("id")
    video_data = video.get("url", {}) or {}  # PW nests stream info here
    thumbnail = (
        video.get("imageUrl")
        or video.get("thumbnail")
        or video_data.get("thumbnailUrl")
    )
    duration = video.get("duration") or video_data.get("duration")

    await conn.execute(
        """
        INSERT INTO videos (
            id, batch_id, topic_id, title, video_key,
            duration_secs, thumbnail_url, video_type,
            pw_url, subject_id, subject_slug, topic_slug
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        ON CONFLICT (id) DO UPDATE
            SET title         = EXCLUDED.title,
                video_key     = EXCLUDED.video_key,
                duration_secs = EXCLUDED.duration_secs,
                thumbnail_url = EXCLUDED.thumbnail_url,
                pw_url        = EXCLUDED.pw_url
        """,
        vid_id,
        batch_id,
        topic_id,
        video.get("topic") or video.get("title") or "Untitled",
        video.get("videoId") or vid_id,
        int(duration) if duration else None,
        thumbnail,
        video.get("videoType", "pw"),
        pw_url,
        subject_id,
        subject_slug,
        topic_slug,
    )


async def scrape(batch_id: str, subject_id_filter: Optional[str] = None):
    if not AUTH_TOKEN:
        console.print("[red]PW_AUTH_TOKEN not set in .env[/red]")
        sys.exit(1)

    conn = await asyncpg.connect(DATABASE_URL)
    async with httpx.AsyncClient(timeout=30) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # --- Batch ---
            task = progress.add_task("Fetching batch info...", total=None)
            batch_info = await fetch_batch_info(client, batch_id)
            await upsert_batch(conn, {**batch_info, "_id": batch_id})
            progress.update(task, description=f"Batch: {batch_info.get('name', batch_id)}")

            # --- Subjects ---
            progress.update(task, description="Fetching subjects...")
            subjects = await fetch_subjects(client, batch_id)
            if subject_id_filter:
                subjects = [s for s in subjects if (s.get("_id") or s.get("id")) == subject_id_filter]

            for subject in subjects:
                subject_id  = subject.get("_id") or subject.get("id")
                subject_name = subject.get("name", subject_id)
                subject_slug = subject.get("slug", "")

                # --- Topics ---
                progress.update(task, description=f"[{subject_name}] fetching topics...")
                topics = await fetch_topics(client, batch_id, subject_id)

                for order, topic in enumerate(topics):
                    topic_id   = topic.get("_id") or topic.get("id")
                    topic_name = topic.get("name", topic_id)
                    topic_slug = topic.get("slug", "")

                    await upsert_topic(conn, topic, batch_id, order)

                    # --- Videos ---
                    progress.update(task, description=f"[{subject_name}] {topic_name}")
                    raw_videos = await fetch_videos_for_topic(client, batch_id, subject_id, topic_id)

                    for v in raw_videos:
                        vid_id  = v.get("_id") or v.get("id")
                        vid_key = v.get("videoId") or vid_id
                        # Fetch signed stream URL
                        pw_url = await fetch_video_url(client, vid_id, vid_key)
                        await upsert_video(
                            conn, v, batch_id, topic_id,
                            subject_id, subject_slug, topic_slug, pw_url
                        )
                        console.print(f"  ✓ {v.get('topic') or v.get('title') or vid_id}")

    await conn.close()
    console.print("[green]Scrape complete.[/green]")


@app.command()
def main(
    batch_id: str = typer.Option(..., "--batch-id", help="PW batch ID to scrape"),
    subject_id: Optional[str] = typer.Option(None, "--subject-id", help="Limit to one subject"),
):
    asyncio.run(scrape(batch_id, subject_id))


if __name__ == "__main__":
    app()
