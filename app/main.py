from fastapi import FastAPI

from app.domain.exceptions.user_exceptions import DomainError
from app.infrastructure.api.exception_handlers import domain_exception_handler
from app.infrastructure.api.routes.user import router as user_router

app = FastAPI(title='TurfBoor User Service')

app.include_router(user_router)
app.add_exception_handler(DomainError, domain_exception_handler)
