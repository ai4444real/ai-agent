from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.actions_api import router as actions_router
from app.models import HealthResponse
from app.things_api import router as things_router

app = FastAPI(title="Minimal Accountability Server", version="0.1.0")
static_dir = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/health.html", include_in_schema=False)
def health_html() -> FileResponse:
    return FileResponse(static_dir / "health.html")


app.include_router(things_router)
app.include_router(actions_router)
