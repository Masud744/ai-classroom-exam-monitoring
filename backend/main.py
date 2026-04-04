from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.logs import router as logs_router
from backend.routes.auth import router as auth_router

app = FastAPI(title="AI Exam Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")

@app.get("/")
def root():
    return {"message": "AI Exam Monitoring API is running"}