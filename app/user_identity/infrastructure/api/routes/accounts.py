from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from app.user_identity.domain.ports.input.block_account_port import BlockAccountPort
from app.user_identity.domain.ports.input.unblock_account_port import (
    UnblockAccountPort,
)
from app.user_identity.infrastructure.api.api_docs.accounts import (
    CHANGE_ACCOUNT_STATUS_DOCS,
    CHANGE_ACCOUNT_STATUS_REQUEST_EXAMPLES,
)
from app.user_identity.infrastructure.api.dependencies import (
    get_block_account_use_case,
    get_unblock_account_use_case,
    require_turfbook_api_key,
)
from app.user_identity.infrastructure.api.schemas.account_schema import (
    AccountOperation,
    AccountStatusData,
    AccountStatusRequest,
)
from app.user_identity.infrastructure.api.schemas.api_response import ApiResponse

router = APIRouter(dependencies=[Depends(require_turfbook_api_key)])


@router.patch(
    '/accounts/{user_uuid}',
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[AccountStatusData],
    **CHANGE_ACCOUNT_STATUS_DOCS,
)
async def change_account_status(
    user_uuid: UUID,
    request: Annotated[
        AccountStatusRequest,
        Body(openapi_examples=CHANGE_ACCOUNT_STATUS_REQUEST_EXAMPLES),
    ],
    block: BlockAccountPort = Depends(get_block_account_use_case),
    unblock: UnblockAccountPort = Depends(get_unblock_account_use_case),
) -> ApiResponse[AccountStatusData]:
    """TurfBook blocks or unblocks any account, for any reason; its user is told by
    email and SMS. A blocked account is closed after 7 days, unless it is unblocked.
    Needs TurfBook's API key in the X-Api-Key header."""
    use_case = block if request.operation is AccountOperation.BLOCK else unblock
    new_status, changed_at = await use_case.execute(user_uuid)
    data = AccountStatusData(
        user_uuid=user_uuid, status=new_status, changed_at=changed_at
    )
    return ApiResponse(success=True, data=data)
