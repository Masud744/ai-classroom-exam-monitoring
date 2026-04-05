from fastapi import APIRouter
from backend.models import MonitoringLog
from backend.database import supabase

router = APIRouter()

@router.post("/log")
def save_log(log: MonitoringLog):
    data = log.dict()
    response = supabase.table("monitoring_logs").insert(data).execute()

    # Suspicious score >= 50 triggers an alert
    if log.suspicious_score >= 50:
        alert_data = {
            "alert_type": "high_suspicious",
            "suspicious_score": log.suspicious_score,
            "description": build_alert_description(log)
        }
        supabase.table("alerts").insert(alert_data).execute()

    return {"status": "saved", "data": response.data}

def build_alert_description(log: MonitoringLog) -> str:
    reasons = []
    if log.phone_detected:
        reasons.append("Phone detected")
    if not log.looking_forward:
        reasons.append("Not looking forward")
    if log.talking:
        reasons.append("Talking")
    if log.eyes_closed:
        reasons.append("Eyes closed")
    if log.multiple_faces:
        reasons.append("Multiple faces")
    if not log.face_present:
        reasons.append("No face detected")
    return ", ".join(reasons) if reasons else "Suspicious behavior"

@router.get("/logs/{student_id}")
def get_logs(student_id: str):
    response = supabase.table("monitoring_logs")\
        .select("*")\
        .eq("student_id", student_id)\
        .order("created_at", desc=True)\
        .execute()
    return {"logs": response.data}

@router.get("/logs")
def get_all_logs():
    response = supabase.table("monitoring_logs")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(100)\
        .execute()
    return {"logs": response.data}

@router.get("/alerts")
def get_alerts():
    response = supabase.table("alerts")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(50)\
        .execute()
    return {"alerts": response.data}

@router.get("/students")
def get_students():
    response = supabase.table("monitoring_logs")\
        .select("student_id")\
        .execute()
    ids = list(set([r["student_id"] for r in response.data]))
    return {"students": ids}