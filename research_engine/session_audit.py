"""Classify 5-minute bar timestamp gaps against verified TMF session boundaries.

This module does not infer exchange holidays or decide that a long closure is
valid. It only recognizes the timestamp boundaries present in the checked-in
TMFR1 file; holiday-calendar validation remains a separate step.
"""
from datetime import datetime


def classify_tmfr1_interval(previous: datetime, current: datetime) -> str:
    """Classify an adjacent-bar interval without changing either record."""
    seconds = (current - previous).total_seconds()
    if seconds == 300:
        return "continuous_5m"

    previous_time = previous.time().replace(tzinfo=None)
    current_time = current.time().replace(tzinfo=None)

    # Regular day session ends with a bar stamped 13:40; monthly expiry
    # sessions can end with a 13:25 bar. The after-hours session opens 15:00.
    if previous_time.strftime("%H:%M:%S") in {"13:25:00", "13:40:00"} and current_time.strftime("%H:%M:%S") == "15:00:00":
        return "day_to_after_hours"

    # After-hours bars run through 04:55; the next day session starts 08:45.
    # The elapsed time may be longer across weekends or exchange holidays.
    if previous_time.strftime("%H:%M:%S") == "04:55:00" and current_time.strftime("%H:%M:%S") == "08:45:00":
        return "after_hours_to_day"

    return "unexpected_interval"
