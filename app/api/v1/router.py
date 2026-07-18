from fastapi import APIRouter

from app.api.v1.routers import auth, categories, exercises, health, me, reports, search, students, trainings, uploads

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["Health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_v1_router.include_router(search.router, prefix="/search", tags=["Search"])
api_v1_router.include_router(students.router, prefix="/students", tags=["Students"])
api_v1_router.include_router(exercises.router, prefix="/exercises", tags=["Exercises"])
api_v1_router.include_router(categories.router, prefix="/training-categories", tags=["Training Categories"])
api_v1_router.include_router(trainings.router, prefix="/trainings", tags=["Trainings"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_v1_router.include_router(me.router, prefix="/me", tags=["Student Area"])
api_v1_router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
