import json
import logging
import time
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest
from botocore.stub import ANY, Stubber

from app.user_identity.domain.entities.notice import Notice, NoticeRecipient, Notifier
from app.user_identity.domain.exceptions import NoticeNotPublishedError
from app.user_identity.infrastructure.messaging.sns_notice_publisher import (
    SnsNoticePublisher,
    sns_client,
)

# SNS cannot run locally: these tests replace it with botocore's Stubber, or point
# the client at an address that never answers.
TOPIC_ARN = 'arn:aws:sns:us-east-1:123456789012:turfbook-notifications-dev-notices'
TIMEOUT_SECONDS = 1.0
NOTICE = Notice(
    notice_id=UUID('6f1c2a9e-0b7d-4c1e-9a55-2f3e8d1b7c40'),
    notifiers=(Notifier.EMAIL, Notifier.SMS),
    recipient=NoticeRecipient(
        uuid=UUID('0b8e7a52-3c1d-4f6e-8a90-1d2c3b4a5e6f'),
        email='luis.h@gmail.com',
        cellphone='+51987654321',
        first_name='luis',
    ),
    subject='Tu cuenta de TurfBook fue bloqueada',
    body='Hola Luis, tu cuenta de TurfBook fue bloqueada por 5 intentos fallidos.',
)


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake credentials, so the client can sign requests that never reach AWS."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')


def _capturing_client() -> tuple[Any, dict[str, Any]]:
    """A client and the parameters of its next call, as SNS would receive them."""
    client = sns_client(TOPIC_ARN, TIMEOUT_SECONDS)
    sent: dict[str, Any] = {}
    client.meta.events.register(
        'provide-client-params.sns.Publish',
        lambda params, **_: sent.update(params),
    )
    return client, sent


class TestSnsNoticePublisher:
    async def test_publishes_the_notice_as_the_contract_says(self):
        client, sent = _capturing_client()
        with Stubber(client) as stubber:
            stubber.add_response(
                'publish', {'MessageId': 'm-1'}, {'TopicArn': TOPIC_ARN, 'Message': ANY}
            )

            await SnsNoticePublisher(client, TOPIC_ARN).publish(NOTICE)

        assert json.loads(sent['Message']) == {
            'notice_id': '6f1c2a9e-0b7d-4c1e-9a55-2f3e8d1b7c40',
            'notifiers': ['email', 'sms'],
            'recipient': {
                'uuid': '0b8e7a52-3c1d-4f6e-8a90-1d2c3b4a5e6f',
                'email': 'luis.h@gmail.com',
                'cellphone': '+51987654321',
                'first_name': 'luis',
            },
            'subject': 'Tu cuenta de TurfBook fue bloqueada',
            'body': 'Hola Luis, tu cuenta de TurfBook fue bloqueada por 5 intentos '
            'fallidos.',
        }

    async def test_leaves_out_the_email_of_a_recipient_without_one(self):
        notice = replace(
            NOTICE,
            notifiers=(Notifier.SMS,),
            recipient=replace(NOTICE.recipient, email=None),
        )
        client, sent = _capturing_client()
        with Stubber(client) as stubber:
            stubber.add_response('publish', {'MessageId': 'm-1'})

            await SnsNoticePublisher(client, TOPIC_ARN).publish(notice)

        assert 'email' not in json.loads(sent['Message'])['recipient']

    async def test_a_rejected_publication_raises_notice_not_published(self):
        client = sns_client(TOPIC_ARN, TIMEOUT_SECONDS)
        with Stubber(client) as stubber:
            stubber.add_client_error(
                'publish', 'AuthorizationError', http_status_code=403
            )

            with pytest.raises(NoticeNotPublishedError):
                await SnsNoticePublisher(client, TOPIC_ARN).publish(NOTICE)

    async def test_logs_the_failure_with_the_notice_id_and_no_personal_data(
        self, caplog
    ):
        client = sns_client(TOPIC_ARN, TIMEOUT_SECONDS)
        with Stubber(client) as stubber, caplog.at_level(logging.WARNING):
            stubber.add_client_error(
                'publish', 'AuthorizationError', http_status_code=403
            )

            with pytest.raises(NoticeNotPublishedError):
                await SnsNoticePublisher(client, TOPIC_ARN).publish(NOTICE)

        assert str(NOTICE.notice_id) in caplog.text
        assert 'luis.h@gmail.com' not in caplog.text
        assert '+51987654321' not in caplog.text

    async def test_gives_up_within_the_time_limit_when_sns_does_not_answer(
        self, monkeypatch
    ):
        # A private address nobody answers: like SNS without the NAT.
        monkeypatch.setenv('AWS_ENDPOINT_URL_SNS', 'http://10.255.255.1')
        client = sns_client(TOPIC_ARN, TIMEOUT_SECONDS)
        started = time.monotonic()

        with pytest.raises(NoticeNotPublishedError):
            await SnsNoticePublisher(client, TOPIC_ARN).publish(NOTICE)

        assert time.monotonic() - started < TIMEOUT_SECONDS + 0.5


class TestSnsClient:
    def test_works_in_the_region_of_the_topic(self):
        topic_arn = 'arn:aws:sns:eu-west-1:123456789012:turfbook-notifications-dev'

        client = sns_client(topic_arn, TIMEOUT_SECONDS)

        assert client.meta.region_name == 'eu-west-1'
