from fastapi import APIRouter

from app.api import (
    admin,
    auth,
    connectors,
    dashboard,
    notifications,
    profiles,
    removal_requests,
    reports,
    scans,
    schedules,
)
from app.sensitive_monitor.api import router as sensitive_monitor_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(admin.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(profiles.router)
api_router.include_router(scans.router)
api_router.include_router(connectors.router)
api_router.include_router(reports.router)
api_router.include_router(schedules.router)
api_router.include_router(removal_requests.router)
api_router.include_router(notifications.router)
api_router.include_router(sensitive_monitor_router)
