import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.user_identity.domain.entities.notice import Notice
from app.user_identity.domain.exceptions import NoticeNotPublishedError
from app.user_identity.domain.ports.output.notice_publisher_port import (
    NoticePublisherPort,
)
from app.user_identity.infrastructure.messaging.messages import (
    NOTICE_NOT_PUBLISHED_LOG,
)

if TYPE_CHECKING:  # the type stubs are a development dependency
    from types_boto3_sns.client import SNSClient

logger = logging.getLogger(__name__)

# arn:aws:sns:<region>:<account>:<topic>
ARN_REGION_INDEX = 3


def sns_client(topic_arn: str, timeout_seconds: float) -> 'SNSClient':
    """A client in the topic's region that gives up after `timeout_seconds`, in a
    single attempt: botocore has no total limit, so connecting and reading get half
    each."""
    config = Config(
        connect_timeout=timeout_seconds / 2,
        read_timeout=timeout_seconds / 2,
        retries={'total_max_attempts': 1},
    )
    region = topic_arn.split(':')[ARN_REGION_INDEX]
    return boto3.client('sns', region_name=region, config=config)


class SnsNoticePublisher(NoticePublisherPort):
    def __init__(self, client: 'SNSClient', topic_arn: str) -> None:
        self._client = client
        self._topic_arn = topic_arn

    async def publish(self, notice: Notice) -> None:
        try:
            await asyncio.to_thread(
                self._client.publish,
                TopicArn=self._topic_arn,
                Message=json.dumps(_message(notice), ensure_ascii=False),
            )
        except (BotoCoreError, ClientError) as error:
            logger.warning(NOTICE_NOT_PUBLISHED_LOG, notice.notice_id, _reason(error))
            raise NoticeNotPublishedError() from error


def _message(notice: Notice) -> dict[str, Any]:
    """The notice in the contract of notifications. A channel's data that is not
    there is left out: notifications only requires it for the channels it uses."""
    recipient: dict[str, Any] = {
        'uuid': str(notice.recipient.uuid),
        'cellphone': notice.recipient.cellphone,
        'first_name': notice.recipient.first_name,
    }
    if notice.recipient.email is not None:
        recipient['email'] = notice.recipient.email
    return {
        'notice_id': str(notice.notice_id),
        'notifiers': [notifier.value for notifier in notice.notifiers],
        'recipient': recipient,
        'subject': notice.subject,
        'body': notice.body,
    }


def _reason(error: BotoCoreError | ClientError) -> str:
    """The error's code or type: botocore's text may quote the parameters sent,
    which carry the recipient's personal data."""
    if isinstance(error, ClientError):
        return str(error.response.get('Error', {}).get('Code', 'ClientError'))
    return type(error).__name__
