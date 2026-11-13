"""Horaires écrits du monde fictif. Minute zéro = lundi 09:00."""
BASE_MINUTE = 9 * 60


def wait_until_available(minute: int, schedule: dict | None) -> int:
    if not schedule: return 0
    if isinstance(schedule, list): return min((wait_until_available(minute, window) for window in schedule), default=0)
    start, end = schedule.get('start', 0), schedule.get('end', 1440)
    current = (BASE_MINUTE + minute) % 1440
    if start <= end:
        if start <= current < end: return 0
        return start - current if current < start else 1440 - current + start
    if current >= start or current < end: return 0
    return start - current
