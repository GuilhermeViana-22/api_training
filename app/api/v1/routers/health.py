from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    from sqlalchemy import text

    from app.database.session import SessionLocal

    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_status = "disconnected"

    return {"status": "healthy" if db_status == "connected" else "degraded", "database": db_status, "version": "1.0.0"}
