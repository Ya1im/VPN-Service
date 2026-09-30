import pytest

from vpn.models import User
from vpn.xray_config import Reality


@pytest.fixture
def reality():
    return Reality(private_key="PRIV", public_key="PUBKEY", short_id="abcd1234", server_name="46-62-140-16.sslip.io")


@pytest.fixture
def users():
    return [
        User("mom", "11111111-1111-4111-8111-111111111111", "tok1", "2026-10-01T00:00:00+00:00"),
        User("old", "22222222-2222-4222-8222-222222222222", "tok2", "2026-10-01T00:00:00+00:00", active=False),
    ]
