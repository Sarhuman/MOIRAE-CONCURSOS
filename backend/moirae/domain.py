"""Regras puras do primeiro percurso de prática."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FREE_DAILY_LIMIT = 10
SESSION_SIZE = 5


def study_day(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('America/Sao_Paulo')).date().isoformat()


def remaining(used: int) -> int:
    return max(0, FREE_DAILY_LIMIT - used)
