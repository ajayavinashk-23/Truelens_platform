import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.model_loader import load_all_models
from routers import image, video, audio

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

APP_TITLE = os.getenv("APP_TITLE", "Truelens Forensics API")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "Digital media forensics inference API — image, video, and audio deepfake detection.",
)
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

# Allowed origins for cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(image.router)
app.include_router(video.router)
app.include_router(audio.router)


@app.on_event("startup")
def on_startup():
    # Load all pretrained models once, at process start, not per-request.
    load_all_models()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
