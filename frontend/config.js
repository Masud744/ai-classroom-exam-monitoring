const API = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ? "http://localhost:8000/api"
  : "https://ai-classroom-exam-monitoring.onrender.com/api";