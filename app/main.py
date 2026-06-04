import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, aircraft, events, fdm, health, hums
from app.db import SessionLocal, init_db
from app.jobs.hums_poll import run_hums_poll
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.openapi_config import API_DESCRIPTION, OPENAPI_TAGS
from app.services.token_manager import TokenManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _run_startup_seed() -> None:
    try:
        from app.seed import seed_mappings

        seed_mappings()
    except Exception:
        logger.exception("Startup seed failed (continuing)")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    _run_startup_seed()
    db = SessionLocal()
    try:
        TokenManager(db).ensure_token_on_startup()
    finally:
        db.close()
    run_hums_poll()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Brazos GPMS Integration API",
    summary="Mapping-scoped GPMS HUMS + FDM cache for Brazos Safety Systems",
    description=API_DESCRIPTION,
    version="0.2.0",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": False,
    },
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(aircraft.router)
app.include_router(hums.gpms_router)
app.include_router(hums.customer_router)
app.include_router(events.router)
app.include_router(fdm.router)
app.include_router(admin.router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", tags=["portal"], include_in_schema=True)
def portal_home() -> FileResponse:
    """Operator portal (HTML). For REST API use `/docs`."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", include_in_schema=False)
def api_root_redirect() -> RedirectResponse:
    """Shortcut to Swagger UI."""
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/swagger", include_in_schema=False)
def swagger_redirect() -> RedirectResponse:
    """Alias for Swagger UI."""
    return RedirectResponse(url="/docs", status_code=302)
