from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.classifier import load_model
from app.routers import auth, predictions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the model at startup so a missing or stale artifact fails fast."""
    load_model()
    yield


app = FastAPI(title="Phishing Detector API", lifespan=lifespan)
app.include_router(predictions.router)
app.include_router(auth.router)
app.include_router(predictions.router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}