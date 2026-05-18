"""
main.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.database import init_db
from api.economics_router import router
from api.admin_router import router as admin_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="IncuBrix Economics Engine - cost estimation and route recommendation for video generation jobs.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    print(f"=== {settings.app_name} starting ===")
    init_db()
    print("DB ready.")


app.include_router(router)
app.include_router(admin_router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/", tags=["Health"])
def root():
    return {"message": "IncuBrix Economics Engine running.", "docs": "/docs"}
