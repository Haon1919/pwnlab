from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select
import logging

from app.database import init_db, engine
from app.config import settings
from app.routers import auth, scenarios, sessions, wargames, ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def poll_all_wargames():
    """APScheduler task: poll all active wargame sessions."""
    from app.models.wargame import WargameState
    from app.services.wargame_engine import poll_wargame

    with Session(engine) as db:
        active_states = db.exec(
            select(WargameState).where(WargameState.is_active == True)
        ).all()
        for state in active_states:
            await poll_wargame(state.session_id, db)


async def cleanup_stale_sessions():
    """APScheduler task: stop sessions older than SESSION_TIMEOUT_HOURS."""
    from app.models.session import LabSession
    from app.services.session_manager import stop_session
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    with Session(engine) as db:
        stale = db.exec(
            select(LabSession).where(
                LabSession.status.in_(["starting", "running"]),
                LabSession.created_at < cutoff,
            )
        ).all()
        for session in stale:
            logger.info(f"Cleaning up stale session {session.id}")
            try:
                await stop_session(session, db)
            except Exception as e:
                logger.error(f"Error cleaning up session {session.id}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("Database initialized")

    # Start scheduler
    scheduler.add_job(
        poll_all_wargames,
        IntervalTrigger(seconds=5),
        id="poll_wargames",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_stale_sessions,
        IntervalTrigger(minutes=15),
        id="cleanup_sessions",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="PwnLab API",
    description="Docker-based penetration testing lab platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(scenarios.router)
app.include_router(sessions.router)
app.include_router(wargames.router)
app.include_router(ai.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
