from fastapi import APIRouter

from app.user_identity.infrastructure.api.routes.tokens import router as tokens_router
from app.user_identity.infrastructure.api.routes.user import router as user_router

API_VERSION_PREFIX = '/v1'

router = APIRouter(prefix=API_VERSION_PREFIX)
router.include_router(user_router)
router.include_router(tokens_router)
