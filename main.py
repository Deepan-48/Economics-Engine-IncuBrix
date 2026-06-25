from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.database import init_db

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="IncuBrix Economics Engine v2 - intelligence layer for video generation cost management.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def on_startup():
    print(f"=== {settings.app_name} starting ===")
    init_db()
    print("DB ready.")

# v1 routers
from api.economics_router import router as v1_router
from api.admin_router import router as admin_v1_router
app.include_router(v1_router)
app.include_router(admin_v1_router)

# v2 routers
from api_v2.estimate_router import router as estimate_v2
from api_v2.pricing_router import router as pricing_v2
from api_v2.budget_router import router as budget_v2
from api_v2.ledger_router import router as ledger_v2
from api_v2.actuals_router import router as actuals_v2
from api_v2.simulation_router import router as simulation_v2
from api_v2.analytics_router import router as analytics_v2

app.include_router(estimate_v2)
app.include_router(pricing_v2)
app.include_router(budget_v2)
app.include_router(ledger_v2)
app.include_router(actuals_v2)
app.include_router(simulation_v2)
app.include_router(analytics_v2)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}

@app.get("/", tags=["Health"])
def root():
    return {"message": f"{settings.app_name} running.", "docs": "/docs"}
