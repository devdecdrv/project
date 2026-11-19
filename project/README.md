# PW Mirror — Self-Hosted Video Platform

Full-stack platform that scrapes, stores metadata, proxies streams, and serves a clean frontend for PW content.

## Stack
- **Scraper** — Python, fetches batch/video metadata from PW APIs
- **API** — FastAPI, serves video/batch data to frontend
- **Proxy** — Python (aiohttp), streams video chunks from CDN
- **Frontend** — React + Vite
- **DB** — PostgreSQL

## Quick Start

```bash
cp .env.example .env
# Fill in your PW token and other values in .env

docker-compose up --build
```

Frontend: http://localhost:5173  
API docs: http://localhost:8000/docs  
Proxy: http://localhost:8001

## Environment Variables
See `.env.example` for all required variables.

## Architecture

```
User → Frontend (React)
         ↓
       API (FastAPI) ← PostgreSQL
         ↓
       Proxy (aiohttp)
         ↓
       PW CDN / BunnyCDN
```

The proxy sits between the user and PW's CDN. It forwards range requests and streams chunks directly — the user's browser never touches PW's origin directly.
