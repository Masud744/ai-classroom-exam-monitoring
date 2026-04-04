from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import supabase

router = APIRouter()

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "student"

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/signup")
def signup(data: SignupRequest):
    response = supabase.auth.sign_up({
        "email": data.email,
        "password": data.password,
        "options": {
            "data": {
                "full_name": data.full_name,
                "role": data.role
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