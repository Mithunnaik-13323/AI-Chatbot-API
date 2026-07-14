from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_indexes
from app.routers import auth, chat

app = FastAPI(
    title=settings.app_name,
    description="A RESTful backend for AI-powered chatbot conversations with JWT auth and persistent history.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)


@app.on_event("startup")
async def on_startup():
    await init_indexes()


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "service": settings.app_name}


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
