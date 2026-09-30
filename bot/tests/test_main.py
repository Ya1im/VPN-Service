from datetime import datetime, timezone

from app.main import seconds_until


def test_seconds_until_same_day_and_next_day():
    assert seconds_until(7, datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)) == 3600
    assert seconds_until(7, datetime(2026, 10, 1, 7, 0, tzinfo=timezone.utc)) == 86400
