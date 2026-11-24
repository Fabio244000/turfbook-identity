from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.user_identity.domain.entities.security_process import (
    CodeIssuer,
    ProcessFailureReason,
    SecurityCode,
    SecurityCodeStatus,
    SecurityProcess,
    SecurityProcessStatus,
    SecurityProcessType,
)
from app.user_identity.domain.ports.driven.security_process_repository_port import (
    SecurityProcessRepositoryPort,
)
from app.user_identity.infrastructure.database.models import (
    SecurityCodeModel,
    SecurityProcessModel,
)

_OPEN = (SecurityProcessStatus.IN_PROGRESS.value, SecurityProcessStatus.VALIDATED.value)


class SecurityProcessRepository(SecurityProcessRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, process: SecurityProcess) -> None:
        self._session.add(self._to_model(process))
        self._session.add_all(self._to_code_model(code) for code in process.codes)

    async def update(self, process: SecurityProcess) -> None:
        await self._session.merge(self._to_model(process))
        kept = [code.uuid for code in process.codes]
        await self._session.execute(
            delete(SecurityCodeModel).where(
                SecurityCodeModel.process_uuid == process.uuid,
                SecurityCodeModel.uuid.not_in(kept),
            )
        )
        # Oldest first: merge loads each code, which flushes the one before, so the
        # code it replaces leaves `active` before the new one enters it.
        for code in process.codes:
            await self._session.merge(self._to_code_model(code))

    async def get_by_uuid_for_update(
        self, process_uuid: UUID
    ) -> SecurityProcess | None:
        query = select(SecurityProcessModel).where(
            SecurityProcessModel.uuid == process_uuid
        )
        return await self._get(query.with_for_update())

    async def get_open_for_update(
        self, user_uuid: UUID, type: SecurityProcessType
    ) -> SecurityProcess | None:
        query = select(SecurityProcessModel).where(
            SecurityProcessModel.user_uuid == user_uuid,
            SecurityProcessModel.type == type.value,
            SecurityProcessModel.status.in_(_OPEN),
        )
        return await self._get(query.with_for_update())

    async def get_by_uuid(self, process_uuid: UUID) -> SecurityProcess | None:
        query = select(SecurityProcessModel).where(
            SecurityProcessModel.uuid == process_uuid
        )
        return await self._get(query)

    async def has_failed_since(
        self, user_uuid: UUID, type: SecurityProcessType, since: datetime
    ) -> bool:
        query = select(exists().where(*self._failed_since(user_uuid, type, since)))
        return bool((await self._session.execute(query)).scalar())

    async def count_failed_since(
        self, user_uuid: UUID, type: SecurityProcessType, since: datetime
    ) -> int:
        query = (
            select(func.count())
            .select_from(SecurityProcessModel)
            .where(*self._failed_since(user_uuid, type, since))
        )
        return int((await self._session.execute(query)).scalar_one())

    async def last_completed_at(
        self, user_uuid: UUID, type: SecurityProcessType
    ) -> datetime | None:
        query = select(func.max(SecurityProcessModel.finished_at)).where(
            SecurityProcessModel.user_uuid == user_uuid,
            SecurityProcessModel.type == type.value,
            SecurityProcessModel.status == SecurityProcessStatus.COMPLETED.value,
        )
        last: datetime | None = (await self._session.execute(query)).scalar_one()
        return last

    async def delete(self, process_uuid: UUID) -> None:
        await self._delete_codes(SecurityCodeModel.process_uuid == process_uuid)
        await self._session.execute(
            delete(SecurityProcessModel).where(
                SecurityProcessModel.uuid == process_uuid
            )
        )

    async def delete_of_users(self, user_uuids: Sequence[UUID]) -> None:
        processes = select(SecurityProcessModel.uuid).where(
            SecurityProcessModel.user_uuid.in_(user_uuids)
        )
        await self._delete_codes(SecurityCodeModel.process_uuid.in_(processes))
        await self._session.execute(
            delete(SecurityProcessModel).where(
                SecurityProcessModel.user_uuid.in_(user_uuids)
            )
        )

    def _failed_since(
        self, user_uuid: UUID, type: SecurityProcessType, since: datetime
    ) -> tuple[ColumnElement[bool], ...]:
        return (
            SecurityProcessModel.user_uuid == user_uuid,
            SecurityProcessModel.type == type.value,
            SecurityProcessModel.status == SecurityProcessStatus.FAILED.value,
            SecurityProcessModel.finished_at >= since,
        )

    async def _delete_codes(self, condition: ColumnElement[bool]) -> None:
        await self._session.execute(delete(SecurityCodeModel).where(condition))

    async def _get(
        self, query: Select[tuple[SecurityProcessModel]]
    ) -> SecurityProcess | None:
        model = (await self._session.execute(query)).scalar_one_or_none()
        if model is None:
            return None
        codes = await self._session.execute(
            select(SecurityCodeModel)
            .where(SecurityCodeModel.process_uuid == model.uuid)
            .order_by(SecurityCodeModel.created_at)
        )
        return self._to_entity(model, [self._to_code(c) for c in codes.scalars()])

    def _to_model(self, process: SecurityProcess) -> SecurityProcessModel:
        return SecurityProcessModel(
            uuid=process.uuid,
            user_uuid=process.user_uuid,
            type=process.type.value,
            status=process.status.value,
            user_codes=process.user_codes,
            support_codes=process.support_codes,
            password_attempts=process.password_attempts,
            started_at=process.started_at,
            validated_at=process.validated_at,
            finished_at=process.finished_at,
            failure_reason=(
                process.failure_reason.value if process.failure_reason else None
            ),
        )

    def _to_code_model(self, code: SecurityCode) -> SecurityCodeModel:
        return SecurityCodeModel(
            uuid=code.uuid,
            process_uuid=code.process_uuid,
            code=code.code,
            issued_by=code.issued_by.value,
            created_at=code.created_at,
            expires_at=code.expires_at,
            failed_attempts=code.failed_attempts,
            status=code.status.value,
        )

    def _to_entity(
        self, model: SecurityProcessModel, codes: list[SecurityCode]
    ) -> SecurityProcess:
        return SecurityProcess(
            uuid=model.uuid,
            user_uuid=model.user_uuid,
            type=SecurityProcessType(model.type),
            status=SecurityProcessStatus(model.status),
            user_codes=model.user_codes,
            support_codes=model.support_codes,
            password_attempts=model.password_attempts,
            started_at=model.started_at,
            validated_at=model.validated_at,
            finished_at=model.finished_at,
            failure_reason=(
                ProcessFailureReason(model.failure_reason)
                if model.failure_reason
                else None
            ),
            codes=codes,
        )

    def _to_code(self, model: SecurityCodeModel) -> SecurityCode:
        return SecurityCode(
            uuid=model.uuid,
            process_uuid=model.process_uuid,
            code=model.code,
            issued_by=CodeIssuer(model.issued_by),
            created_at=model.created_at,
            expires_at=model.expires_at,
            failed_attempts=model.failed_attempts,
            status=SecurityCodeStatus(model.status),
        )
