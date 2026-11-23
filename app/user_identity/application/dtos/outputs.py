from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SupportSecurityCode:
    """The security code shown to support; `generated` says whether support's
    request created it."""

    process_uuid: UUID
    code: str
    code_expires_at: datetime
    generated: bool
