from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo
from enum import StrEnum
from typing import NoReturn, Self
from uuid import UUID, uuid4

from app.user_identity.domain.entities.password_process_rules import (
    PasswordProcessRules,
)
from app.user_identity.domain.entities.security_code_rules import SecurityCodeRules
from app.user_identity.domain.exceptions import DomainError, DomainErrorCode
from app.user_identity.domain.messages import (
    PASSWORD_ATTEMPTS_EXCEEDED,
    PASSWORD_UPDATE_INTERVAL,
    PROCESS_FAILED,
    PROCESS_NOT_IN_PROGRESS,
    RECOVERY_LIMIT,
    SECURITY_CODE_ALREADY_VALIDATED,
    SECURITY_CODE_DELIVERED,
    SECURITY_CODE_EXHAUSTED,
    SECURITY_CODE_EXPIRED,
    SECURITY_CODE_INCORRECT,
    SECURITY_CODE_LIMIT,
    SECURITY_CODE_NOT_VALIDATED,
    SUPPORT_CODE_LIMIT,
)


class SecurityProcessType(StrEnum):
    EMAIL_VERIFICATION = 'email_verification'
    PASSWORD_UPDATE = 'password_update'
    PASSWORD_RECOVERY = 'password_recovery'


class SecurityProcessStatus(StrEnum):
    IN_PROGRESS = 'in_progress'
    VALIDATED = 'validated'
    COMPLETED = 'completed'
    FAILED = 'failed'
    # Still open at the midnight of the day it started.
    INCOMPLETE = 'incomplete'


class ProcessFailureReason(StrEnum):
    ATTEMPTS = 'attempts'
    DEADLINE = 'deadline'
    PASSWORD_ATTEMPTS = 'password_attempts'


class CodeIssuer(StrEnum):
    USER = 'user'
    TURFBOOK = 'turfbook'


class SecurityCodeStatus(StrEnum):
    # Not sent yet: it does not replace the active code until it is sent.
    PENDING = 'pending'
    ACTIVE = 'active'
    REPLACED = 'replaced'
    USED = 'used'
    EXHAUSTED = 'exhausted'


@dataclass
class SecurityCode:
    process_uuid: UUID
    code: str
    issued_by: CodeIssuer
    created_at: datetime
    expires_at: datetime
    status: SecurityCodeStatus
    failed_attempts: int = 0
    uuid: UUID = field(default_factory=uuid4)

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def record_failed_attempt(self, max_attempts: int) -> None:
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.status = SecurityCodeStatus.EXHAUSTED


@dataclass
class SecurityProcess:
    """A credential process of a user, with its security codes. The user requests and
    validates codes within a window; then only support may generate one, within its
    grace. It closes when nothing is left in force for it, or at the midnight
    (business time zone) of the day it started, whichever comes first."""

    user_uuid: UUID
    type: SecurityProcessType
    started_at: datetime
    status: SecurityProcessStatus = SecurityProcessStatus.IN_PROGRESS
    user_codes: int = 0
    support_codes: int = 0
    # Business rejections of the new password, once the code was validated.
    password_attempts: int = 0
    validated_at: datetime | None = None
    finished_at: datetime | None = None
    failure_reason: ProcessFailureReason | None = None
    codes: list[SecurityCode] = field(default_factory=list)
    uuid: UUID = field(default_factory=uuid4)

    @classmethod
    def start(
        cls,
        user_uuid: UUID,
        type: SecurityProcessType,
        now: datetime,
        failed_today: bool,
    ) -> Self:
        """`failed_today`: a process of this type failed today, which only the stored
        processes know."""
        if failed_today:
            raise DomainError(PROCESS_FAILED, code=DomainErrorCode.PROCESS_FAILED)
        return cls(user_uuid=user_uuid, type=type, started_at=now)

    @classmethod
    def start_password_update(
        cls,
        user_uuid: UUID,
        now: datetime,
        failed_today: bool,
        last_update_at: datetime | None,
        rules: PasswordProcessRules,
    ) -> Self:
        """The interval since the last successful update is checked before the
        failure of today, so an update of today answers with the interval."""
        interval = timedelta(minutes=rules.update_interval_minutes)
        if last_update_at is not None and now - last_update_at < interval:
            raise DomainError(
                PASSWORD_UPDATE_INTERVAL, code=DomainErrorCode.PASSWORD_UPDATE_INTERVAL
            )
        return cls.start(
            user_uuid, SecurityProcessType.PASSWORD_UPDATE, now, failed_today
        )

    @classmethod
    def start_password_recovery(
        cls,
        user_uuid: UUID,
        now: datetime,
        failed_today: bool,
        failed_this_week: int,
        rules: PasswordProcessRules,
    ) -> Self:
        """The failed recoveries of the week are checked before the failure of today."""
        if failed_this_week >= rules.max_failed_recoveries_per_week:
            raise DomainError(RECOVERY_LIMIT, code=DomainErrorCode.RECOVERY_LIMIT)
        return cls.start(
            user_uuid, SecurityProcessType.PASSWORD_RECOVERY, now, failed_today
        )

    @property
    def is_open(self) -> bool:
        return self.status in (
            SecurityProcessStatus.IN_PROGRESS,
            SecurityProcessStatus.VALIDATED,
        )

    @property
    def has_codes(self) -> bool:
        return bool(self.codes)

    def is_of_day(self, now: datetime, zone: tzinfo) -> bool:
        return _day(now, zone) == _day(self.started_at, zone)

    def close_if_ended(
        self, now: datetime, zone: tzinfo, rules: SecurityCodeRules
    ) -> bool:
        """Closes an open process at the first of: the deadline of a validated one
        (it fails), the moment nothing is left in force for it (incomplete) or the
        midnight that ended its day (incomplete); says whether it closed it."""
        if not self.is_open:
            return False
        end, status = self._end(zone, rules)
        if now < end:
            return False
        self.status = status
        self.finished_at = end
        if status is SecurityProcessStatus.FAILED:
            self.failure_reason = ProcessFailureReason.DEADLINE
        return True

    def password_deadline(self, rules: SecurityCodeRules) -> datetime:
        if self.validated_at is None:
            raise ValueError('the process was not validated')
        return self.validated_at + timedelta(minutes=rules.password_deadline_minutes)

    def ensure_may_set_password(self) -> None:
        if self.status is SecurityProcessStatus.FAILED:
            raise DomainError(PROCESS_FAILED, code=DomainErrorCode.PROCESS_FAILED)
        if self.status is SecurityProcessStatus.IN_PROGRESS:
            raise DomainError(
                SECURITY_CODE_NOT_VALIDATED,
                code=DomainErrorCode.SECURITY_CODE_NOT_VALIDATED,
            )
        if self.status is not SecurityProcessStatus.VALIDATED:
            raise DomainError(
                PROCESS_NOT_IN_PROGRESS, code=DomainErrorCode.PROCESS_NOT_IN_PROGRESS
            )

    def reject_password(
        self, rejection: DomainError, now: datetime, rules: PasswordProcessRules
    ) -> NoReturn:
        """Counts a business rejection of the new password; the last one allowed
        fails the process."""
        self.password_attempts += 1
        if self.password_attempts >= rules.max_password_attempts:
            self._fail(now, ProcessFailureReason.PASSWORD_ATTEMPTS)
            raise DomainError(
                PASSWORD_ATTEMPTS_EXCEEDED,
                code=DomainErrorCode.PASSWORD_ATTEMPTS_EXCEEDED,
            )
        raise rejection

    def issue_user_code(
        self, code: str, now: datetime, rules: SecurityCodeRules
    ) -> SecurityCode:
        """A pending code: the active one keeps working until this one is sent. The
        pending codes count for the limit, so concurrent requests never exceed it."""
        self._ensure_not_validated()
        if now >= self._window_end(rules):
            raise DomainError(
                SECURITY_CODE_LIMIT, code=DomainErrorCode.SECURITY_CODE_LIMIT
            )
        requested = self.user_codes + len(self._codes(SecurityCodeStatus.PENDING))
        if requested >= rules.max_user_codes:
            raise DomainError(
                SECURITY_CODE_LIMIT, code=DomainErrorCode.SECURITY_CODE_LIMIT
            )
        return self._add_code(
            code, CodeIssuer.USER, now, rules, SecurityCodeStatus.PENDING
        )

    def activate_code(self, code_uuid: UUID) -> None:
        """The code was sent: it replaces the active one and counts as requested."""
        code = next(c for c in self.codes if c.uuid == code_uuid)
        self._replace_active()
        code.status = SecurityCodeStatus.ACTIVE
        self.user_codes += 1

    def discard_code(self, code_uuid: UUID) -> None:
        """The code could not be sent: it never existed for the user."""
        self.codes = [c for c in self.codes if c.uuid != code_uuid]

    def current_code(self, now: datetime) -> SecurityCode | None:
        active = self._active()
        if active is None or active.is_expired(now):
            return None
        return active

    def issue_support_code(
        self, code: str, now: datetime, rules: SecurityCodeRules
    ) -> SecurityCode:
        """An active code generated by TurfBook, never sent to the user."""
        self._ensure_not_validated()
        self._ensure_support_may_generate(now, rules)
        self._replace_active()
        self.support_codes += 1
        return self._add_code(
            code, CodeIssuer.TURFBOOK, now, rules, SecurityCodeStatus.ACTIVE
        )

    def validate(self, code: str, now: datetime, rules: SecurityCodeRules) -> None:
        """A wrong code counts an attempt on the active code, even when it is a
        replaced or used one; the last attempt of the last code fails the process."""
        self._ensure_in_progress()
        active = self._code_to_validate(now)
        if active.code != code:
            self._reject_wrong_code(active, now, rules)
        active.status = SecurityCodeStatus.USED
        self.status = SecurityProcessStatus.VALIDATED
        self.validated_at = now

    def complete(self, now: datetime) -> None:
        self.status = SecurityProcessStatus.COMPLETED
        self.finished_at = now

    def _end(
        self, zone: tzinfo, rules: SecurityCodeRules
    ) -> tuple[datetime, SecurityProcessStatus]:
        """When the open process closes, and how."""
        midnight = _midnight(_day(self.started_at, zone) + timedelta(days=1), zone)
        if self.status is SecurityProcessStatus.VALIDATED:
            deadline = self.password_deadline(rules)
            if deadline < midnight:
                return deadline, SecurityProcessStatus.FAILED
            return midnight, SecurityProcessStatus.INCOMPLETE
        return min(
            self._abandoned_at(rules), midnight
        ), SecurityProcessStatus.INCOMPLETE

    def _abandoned_at(self, rules: SecurityCodeRules) -> datetime:
        """When nothing is left in force: the user's window, the active code and
        support's grace, while support may still generate a code."""
        limits = [self._window_end(rules)]
        active = self._active()
        if active is not None:
            limits.append(active.expires_at)
        grace_end = self._support_grace_end(rules)
        if grace_end is not None:
            limits.append(grace_end)
        return max(limits)

    def _support_grace_end(self, rules: SecurityCodeRules) -> datetime | None:
        last = self._last_code()
        if (
            last is None
            or last.status is SecurityCodeStatus.EXHAUSTED
            or self.support_codes >= rules.max_support_codes
        ):
            return None
        return last.expires_at + timedelta(minutes=rules.support_grace_minutes)

    def _window_end(self, rules: SecurityCodeRules) -> datetime:
        return self.started_at + timedelta(minutes=rules.user_window_minutes)

    def _ensure_not_validated(self) -> None:
        """A validated process only ends by setting the new password."""
        if self.status is SecurityProcessStatus.VALIDATED:
            raise DomainError(
                SECURITY_CODE_ALREADY_VALIDATED,
                code=DomainErrorCode.SECURITY_CODE_ALREADY_VALIDATED,
            )

    def _fail(self, now: datetime, reason: ProcessFailureReason) -> None:
        self.status = SecurityProcessStatus.FAILED
        self.finished_at = now
        self.failure_reason = reason

    def _ensure_in_progress(self) -> None:
        if self.status is SecurityProcessStatus.FAILED:
            raise DomainError(PROCESS_FAILED, code=DomainErrorCode.PROCESS_FAILED)
        if self.status is not SecurityProcessStatus.IN_PROGRESS:
            raise DomainError(
                PROCESS_NOT_IN_PROGRESS, code=DomainErrorCode.PROCESS_NOT_IN_PROGRESS
            )

    def _ensure_support_may_generate(
        self, now: datetime, rules: SecurityCodeRules
    ) -> None:
        """A code whose attempts were spent reached the user, who is guessing. The
        grace period needs no check: once it ends, the process is closed."""
        last = self._last_code()
        if last is not None and last.status is SecurityCodeStatus.EXHAUSTED:
            raise DomainError(
                SECURITY_CODE_DELIVERED, code=DomainErrorCode.SECURITY_CODE_DELIVERED
            )
        if self.support_codes >= rules.max_support_codes:
            raise DomainError(
                SUPPORT_CODE_LIMIT, code=DomainErrorCode.SUPPORT_CODE_LIMIT
            )

    def _code_to_validate(self, now: datetime) -> SecurityCode:
        """The active code; an expired one is rejected without counting an attempt."""
        active = self._active()
        if active is None:
            raise DomainError(
                SECURITY_CODE_EXHAUSTED, code=DomainErrorCode.SECURITY_CODE_EXHAUSTED
            )
        if active.is_expired(now):
            raise DomainError(
                SECURITY_CODE_EXPIRED, code=DomainErrorCode.SECURITY_CODE_EXPIRED
            )
        return active

    def _reject_wrong_code(
        self, active: SecurityCode, now: datetime, rules: SecurityCodeRules
    ) -> None:
        active.record_failed_attempt(rules.max_attempts)
        spent = active.status is SecurityCodeStatus.EXHAUSTED
        if spent and self.user_codes >= rules.max_user_codes:
            self._fail(now, ProcessFailureReason.ATTEMPTS)
        raise DomainError(
            SECURITY_CODE_INCORRECT, code=DomainErrorCode.SECURITY_CODE_INCORRECT
        )

    def _add_code(
        self,
        code: str,
        issued_by: CodeIssuer,
        now: datetime,
        rules: SecurityCodeRules,
        status: SecurityCodeStatus,
    ) -> SecurityCode:
        new = SecurityCode(
            process_uuid=self.uuid,
            code=code,
            issued_by=issued_by,
            created_at=now,
            expires_at=now + timedelta(minutes=rules.code_minutes),
            status=status,
        )
        self.codes.append(new)
        return new

    def _active(self) -> SecurityCode | None:
        return next(iter(self._codes(SecurityCodeStatus.ACTIVE)), None)

    def _last_code(self) -> SecurityCode | None:
        sent = [c for c in self.codes if c.status is not SecurityCodeStatus.PENDING]
        return max(sent, key=lambda c: c.created_at, default=None)

    def _replace_active(self) -> None:
        active = self._active()
        if active is not None:
            active.status = SecurityCodeStatus.REPLACED

    def _codes(self, status: SecurityCodeStatus) -> list[SecurityCode]:
        return [c for c in self.codes if c.status is status]


def start_of_day(moment: datetime, zone: tzinfo) -> datetime:
    return _midnight(_day(moment, zone), zone)


def start_of_week(moment: datetime, zone: tzinfo) -> datetime:
    """Monday at 00:00 of the week of the moment."""
    day = _day(moment, zone)
    return _midnight(day - timedelta(days=day.weekday()), zone)


def _midnight(day: date, zone: tzinfo) -> datetime:
    return datetime.combine(day, time(), tzinfo=zone)


def _day(moment: datetime, zone: tzinfo) -> date:
    return moment.astimezone(zone).date()
