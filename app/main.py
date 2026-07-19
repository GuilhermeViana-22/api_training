import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.handlers import register_exception_handlers
from app.database.session import SessionLocal
from app.services.auth_service import seed_admin
from app.services.category_service import seed_categories

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    upload_path = Path(settings.upload_dir)
    (upload_path / "students").mkdir(parents=True, exist_ok=True)
    (upload_path / "exercises").mkdir(parents=True, exist_ok=True)
    (upload_path / "avatars").mkdir(parents=True, exist_ok=True)

    try:
        db = SessionLocal()
        try:
            seed_admin(db)
            seed_categories(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Falha ao conectar/seed no banco — API sobe mesmo assim (/health disponivel)")

    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=settings.app_debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def root_health():
    return {"status": "healthy", "service": settings.app_name}
