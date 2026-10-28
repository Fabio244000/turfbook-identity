from app.migrations.alembic_migrator import AlembicMigrator
from app.migrations.custom_resource import handle_migration_event
from app.migrations.handler import ALEMBIC_INIT_PATH
from tests.fakes.migrations import FakeResponseSender


def test_running_migrations_twice_is_idempotent() -> None:
    event: dict[str, object] = {
        'RequestType': 'Update',
        'ResponseURL': 'https://cloudformation-custom-resource-response.s3.amazonaws.com/x',
        'StackId': 'arn:aws:cloudformation:us-east-1:123456789012:stack/test/abc',
        'RequestId': 'request-123',
        'LogicalResourceId': 'MigrationTrigger',
    }
    migrator, sender = AlembicMigrator(ALEMBIC_INIT_PATH), FakeResponseSender()

    handle_migration_event(event, migrator, sender)
    handle_migration_event(event, migrator, sender)

    assert [body['Status'] for _, body in sender.sent] == ['SUCCESS', 'SUCCESS']
