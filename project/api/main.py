import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.database import get_pool, close_pool
from routes.videos import router as videos_router
from routes.batches import router as batches_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()   # warm up pool on startup
    yield
    await close_pool()


app = FastAPI(title="PW Mirror API", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos_router)
app.include_router(batches_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
