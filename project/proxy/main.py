"""
Stream Proxy
------------
Accepts:  GET /stream?url=<encoded_upstream_url>
          GET /m3u8?url=<encoded_m3u8_url>   (rewrites .ts segment URLs to go through proxy too)

The client never contacts PW's CDN directly.
Supports Range requests so seek works properly in browsers.
"""

import os
import re
import urllib.parse
import asyncio

import aiohttp
import aiohttp_cors
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

PROXY_BASE_URL = os.getenv("PROXY_BASE_URL", "http://localhost:8001")

# Headers forwarded upstream to PW/CDN
UPSTREAM_HEADERS = {
    "User-Agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":     "https://www.pw.live/",
    "Origin":      "https://www.pw.live",
}

CHUNK_SIZE = 65536  # 64 KB chunks


async def stream_handler(request: web.Request) -> web.StreamResponse:
    """
    Proxies a direct video URL (mp4 / .ts segment).
    Passes through Range header for seek support.
    """
    raw_url = request.rel_url.query.get("url")
    if not raw_url:
        return web.Response(status=400, text="Missing url param")

    upstream_url = urllib.parse.unquote(raw_url)

    headers = dict(UPSTREAM_HEADERS)
    if "Range" in request.headers:
        headers["Range"] = request.headers["Range"]

    async with aiohttp.ClientSession() as session:
        async with session.get(upstream_url, headers=headers) as upstream:
            # Build response with same status (200 or 206 for range)
            response = web.StreamResponse(
                status=upstream.status,
                headers={
                    "Content-Type":   upstream.headers.get("Content-Type", "video/mp4"),
                    "Accept-Ranges":  "bytes",
                    "Cache-Control":  "no-store",
                    "Access-Control-Allow-Origin": "*",
                    **(
                        {"Content-Range": upstream.headers["Content-Range"]}
                        if "Content-Range" in upstream.headers
                        else {}
                    ),
                    **(
                        {"Content-Length": upstream.headers["Content-Length"]}
                        if "Content-Length" in upstream.headers
                        else {}
                    ),
                },
            )
            await response.prepare(request)

            async for chunk in upstream.content.iter_chunked(CHUNK_SIZE):
                await response.write(chunk)

            await response.write_eof()
            return response


async def m3u8_handler(request: web.Request) -> web.Response:
    """
    Fetches an HLS m3u8 playlist and rewrites all .ts / .m3u8 segment
    URLs so they route back through this proxy.
    """
    raw_url = request.rel_url.query.get("url")
    if not raw_url:
        return web.Response(status=400, text="Missing url param")

    upstream_url = urllib.parse.unquote(raw_url)
    base_url = upstream_url.rsplit("/", 1)[0] + "/"

    async with aiohttp.ClientSession() as session:
        async with session.get(upstream_url, headers=UPSTREAM_HEADERS) as r:
            if r.status != 200:
                return web.Response(status=r.status, text="Upstream error")
            content = await r.text()

    rewritten_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            rewritten_lines.append(line)
            continue
        if not stripped:
            rewritten_lines.append(line)
            continue

        # Resolve relative URLs
        if stripped.startswith("http"):
            segment_url = stripped
        else:
            segment_url = base_url + stripped

        encoded = urllib.parse.quote(segment_url, safe="")

        if stripped.endswith(".m3u8"):
            rewritten_lines.append(f"{PROXY_BASE_URL}/m3u8?url={encoded}")
        else:
            # .ts or any other segment
            rewritten_lines.append(f"{PROXY_BASE_URL}/stream?url={encoded}")

    rewritten = "\n".join(rewritten_lines)
    return web.Response(
        body=rewritten.encode(),
        content_type="application/vnd.apple.mpegurl",
        headers={"Access-Control-Allow-Origin": "*"},
    )


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/stream", stream_handler)
    app.router.add_get("/m3u8",   m3u8_handler)
    app.router.add_get("/health", lambda _: web.json_response({"status": "ok"}))

    cors = aiohttp_cors.setup(
        app,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=False,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["GET", "OPTIONS"],
            )
        },
    )
    for route in list(app.router.routes()):
        cors.add(route)

    return app


if __name__ == "__main__":
    web.run_app(build_app(), host="0.0.0.0", port=8001)
