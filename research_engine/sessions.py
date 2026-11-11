"""Configurable session classification; no exchange hours are hard-coded."""
from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start: time
    end: time

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("session name cannot be blank")
        if self.start == self.end:
            raise ValueError("session start and end cannot be equal")


def classify_session(timestamp: datetime, sessions: list[SessionWindow]) -> str | None:
    """Return the matching session name, using [start, end) boundaries.

    Overnight windows (for example 23:00–02:00) are supported. If windows
    overlap, classification is rejected rather than choosing arbitrarily.
    The caller is responsible for converting timestamps to the intended
    exchange-local timezone before classification.
    """
    current = timestamp.timetz().replace(tzinfo=None)
    matches: list[str] = []
    for session in sessions:
        if session.start < session.end:
            matched = session.start <= current < session.end
        else:
            matched = current >= session.start or current < session.end
        if matched:
            matches.append(session.name)
    if len(matches) > 1:
        raise ValueError(f"overlapping session windows at {timestamp.isoformat()}: {matches}")
    return matches[0] if matches else None


def validate_session_windows(sessions: list[SessionWindow]) -> list[str]:
    """Detect duplicate names and overlaps on a minute-resolution daily clock."""
    errors: list[str] = []
    names = [session.name for session in sessions]
    if len(names) != len(set(names)):
        errors.append("session names must be unique")
    for minute in range(24 * 60):
        point = time(minute // 60, minute % 60)
        active = []
        for session in sessions:
            if session.start < session.end:
                matched = session.start <= point < session.end
            else:
                matched = point >= session.start or point < session.end
            if matched:
                active.append(session.name)
        if len(active) > 1:
            errors.append(f"overlapping sessions at {point.isoformat()}: {active}")
            break
    return errors
