from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import supabase

router = APIRouter()


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "student"
    student_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/signup")
def signup(data: SignupRequest):
    try:
        response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name":  data.full_name,
                    "role":       data.role,
                    "student_id": data.student_id
                }
            }
        })
        if response.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        return {"message": "Signup successful. Please check your email to verify.", "user": response.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(data: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email":    data.email,
            "password": data.password
        })
        if response.session is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        return {
            "access_token": response.session.access_token,
            "user":         response.user
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    try:
        supabase.auth.reset_password_for_email(
            data.email,
            {"redirect_to": "https://ai-classroom-exam-monitoring.onrender.com/reset-password"}
        )
        return {"message": "Reset email sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))