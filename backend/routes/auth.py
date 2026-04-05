from fastapi import APIRouter
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
    response = supabase.auth.sign_up({
        "email": data.email,
        "password": data.password,
        "options": {
            "data": {
                "full_name": data.full_name,
                "role": data.role,
                "student_id": data.student_id
            }
        }
    })
    return {"message": "Signup successful", "user": response.user}


@router.post("/login")
def login(data: LoginRequest):
    response = supabase.auth.sign_in_with_password({
        "email": data.email,
        "password": data.password
    })
    return {
        "access_token": response.session.access_token,
        "user": response.user
    }


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    supabase.auth.reset_password_email(data.email)
    return {"message": "Reset email sent"}