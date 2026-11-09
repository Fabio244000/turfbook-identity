from fastapi import APIRouter

from app.user_identity.infrastructure.api.routes.accounts import (
    router as accounts_router,
)
from app.user_identity.infrastructure.api.v1_router import API_VERSION_PREFIX

router = APIRouter(prefix=API_VERSION_PREFIX)
router.include_router(accounts_router)
