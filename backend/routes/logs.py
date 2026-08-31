from fastapi import APIRouter
from backend.models import MonitoringLog
from backend.database import supabase

router = APIRouter()


@router.post("/log")
def save_log(log: MonitoringLog):
    data = log.dict()
    response = supabase.table("monitoring_logs").insert(data).execute()

    if log.suspicious_score >= 50:
        alert_data = {
            "alert_type":      "high_suspicious",
            "suspicious_score": log.suspicious_score,
            "description":     build_alert_description(log)
        }
        supabase.table("alerts").insert(alert_data).execute()

    return {"status": "saved", "data": response.data}


def build_alert_description(log: MonitoringLog) -> str:
    reasons = []
    if log.phone_detected:   reasons.append("Phone detected")
    if not log.looking_forward: reasons.append("Not looking forward")
    if log.talking:          reasons.append("Talking")
    if log.eyes_closed:      reasons.append("Eyes closed")
    if log.multiple_faces:   reasons.append("Multiple faces")
    if not log.face_present: reasons.append("No face detected")
    return ", ".join(reasons) if reasons else "Suspicious behavior"


def fetch_all_logs_paginated(student_id: str = None, max_rows: int = 10000):
    all_data = []
    batch_size = 1000
    offset = 0
    while offset < max_rows:
        query = supabase.table("monitoring_logs").select("*")
        if student_id:
            query = query.eq("student_id", student_id)
        query = query.order("created_at", desc=True).range(offset, offset + batch_size - 1)
        res = query.execute()
        if not res.data:
            break
        all_data.extend(res.data)
        if len(res.data) < batch_size:
            break
        offset += batch_size
    return all_data


@router.get("/logs/{student_id}")
def get_logs(student_id: str):
    data = fetch_all_logs_paginated(student_id=student_id)
    return {"logs": data}


@router.get("/logs")
def get_all_logs():
    data = fetch_all_logs_paginated()
    return {"logs": data}


@router.get("/alerts")
def get_alerts():
    response = supabase.table("alerts")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(200)\
        .execute()
    return {"alerts": response.data}


@router.get("/students")
def get_students():
    # Fetch across all recent logs to find all active students
    all_rows = []
    batch_size = 1000
    offset = 0
    while offset < 10000:
        res = supabase.table("monitoring_logs")\
            .select("student_id, student_name")\
            .order("created_at", desc=True)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        if not res.data:
            break
        all_rows.extend(res.data)
        if len(res.data) < batch_size:
            break
        offset += batch_size

    seen = {}
    for r in all_rows:
        sid = r.get("student_id")
        if sid and sid not in seen:
            seen[sid] = r.get("student_name") or sid
    students = [{"id": k, "name": v} for k, v in seen.items()]
    return {"students": students}