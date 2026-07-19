import datetime
from datetime import timezone

_mock_now = None

def get_now() -> datetime.datetime:
    if _mock_now is not None:
        return _mock_now
    return datetime.datetime.now(timezone.utc)

def set_mock_now(dt: datetime.datetime | None) -> None:
    global _mock_now
    _mock_now = dt
