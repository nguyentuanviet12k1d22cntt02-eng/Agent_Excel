"""API REST v1 (docs/thiet-ke/openapi.yaml). Mỗi nhóm tài nguyên một file, gom lại ở `api_router`."""

from fastapi import APIRouter

from tutor_backend.api.v1 import auth, classes, exercises, textbooks, users

api_router = APIRouter()
for module in (auth, users, classes, textbooks, exercises):
    api_router.include_router(module.router)
