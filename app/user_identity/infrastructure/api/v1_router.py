from fastapi import APIRouter

from app.user_identity.infrastructure.api.routes.email_verifications import (
    router as email_verifications_router,
)
from app.user_identity.infrastructure.api.routes.password_recoveries import (
    router as password_recoveries_router,
)
from app.user_identity.infrastructure.api.routes.password_updates import (
    router as password_updates_router,
)
from app.user_identity.infrastructure.api.routes.sessions import (
    router as sessions_router,
)
from app.user_identity.infrastructure.api.routes.tokens import router as tokens_router
from app.user_identity.infrastructure.api.routes.user import router as user_router

API_VERSION_PREFIX = '/v1'

router = APIRouter(prefix=API_VERSION_PREFIX)
router.include_router(user_router)
router.include_router(sessions_router)
router.include_router(tokens_router)
router.include_router(email_verifications_router)
router.include_router(password_updates_router)
router.include_router(password_recoveries_router)
