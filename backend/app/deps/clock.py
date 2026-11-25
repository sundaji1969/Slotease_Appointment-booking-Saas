from datetime import UTC, datetime


def get_now() -> datetime:
    """Injected clock — tests override this dependency to freeze time."""
    return datetime.now(UTC)
