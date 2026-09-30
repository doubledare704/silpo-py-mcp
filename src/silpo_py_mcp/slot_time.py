"""Timeslot bound normalization for ``silpo_get_time_slots``.

Single-responsibility home for the ``start``/``end`` date normalizer shared by
the typed client (pre-request validation) and the in-memory mock (window
filtering). Mirrors the server behavior:

* release-1.111.1: millisecond fractions are stripped upstream;
* release-1.111.2: ``Z``, ``+00:00`` and naive stamps are read as UTC while
  date-only/unparseable values are rejected with ``400``;
* release-1.111.4: the normalizer is more lenient — surrounding whitespace,
  lowercase ``z``, comma fractions, ``+HHMM``/``+HH`` offsets and a space
  separator are all accepted and read the same way.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

_MILLIS_RE = re.compile(r"[.,]\d+(?=(Z|z|[+-]\d{2}:?\d{2}|$))")
_OFFSET_COMPACT_RE = re.compile(r"([+-]\d{2})(\d{2})$")
_OFFSET_HOUR_ONLY_RE = re.compile(r"([+-]\d{2})$")
_TIME_PRESENT_RE = re.compile(r"[T ]\d{1,2}:\d{2}")
_ZULU_SUFFIX_RE = re.compile(r"[Zz]$")


def strip_millis(value: str) -> str:
    """Strip sub-second fractions from an ISO timestamp.

    Handles both ``.`` and ``,`` fractions (``Date#toISOString()``-style
    ``...:00.123Z``) so the value validates against older servers too.
    """
    return _MILLIS_RE.sub("", value)


def _normalize_wire_format(trimmed: str) -> str:
    """Apply wire-format cleanups: ``z`` → ``Z``, offsets → ``±HH:MM``."""
    normalized = _ZULU_SUFFIX_RE.sub("Z", trimmed)
    if re.search(r"[+-]\d{4}$", normalized):
        normalized = _OFFSET_COMPACT_RE.sub(r"\1:\2", normalized)
    elif _OFFSET_HOUR_ONLY_RE.search(normalized):
        normalized = f"{normalized}:00"
    return normalized


def _parse_candidate(normalized: str) -> datetime:
    candidate = normalized
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    return datetime.fromisoformat(candidate)


def normalize_slot_bound(value: str, *, field: str) -> str:
    """Validate and normalize a ``get_time_slots`` ``start``/``end`` bound.

    Accepts ``Z``/``z``, explicit offsets (``+00:00``, ``+0000``, ``+00``) and
    naive stamps — all read as UTC — plus surrounding whitespace, comma
    fractions and a space separator. Returns the wire string with
    milliseconds stripped and the offset in canonical ``±HH:MM`` form
    (``Z`` preserved). Raises ``ValueError`` with an actionable message for
    date-only or unparseable input instead of surfacing a raw ``400``.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"get_time_slots {field}={value!r} is not a valid ISO date-time. "
            "Use a full timestamp (e.g. '2026-09-28T10:00:00+00:00' or "
            "'2026-09-28T10:00:00Z'); date-only values are rejected by the server."
        )
    normalized = _normalize_wire_format(strip_millis(value.strip()))
    if not _TIME_PRESENT_RE.search(normalized):
        raise ValueError(
            f"get_time_slots {field}={value!r} is not a valid ISO date-time. "
            "Use a full timestamp (e.g. '2026-09-28T10:00:00+00:00' or "
            "'2026-09-28T10:00:00Z'); date-only values are rejected by the server."
        )
    try:
        _parse_candidate(normalized)
    except ValueError:
        raise ValueError(
            f"get_time_slots {field}={value!r} is not a valid ISO date-time. "
            "Use a full timestamp (e.g. '2026-09-28T10:00:00+00:00' or "
            "'2026-09-28T10:00:00Z'); date-only values are rejected by the server."
        ) from None
    return normalized


def parse_slot_bound(value: str, field: str) -> datetime:
    """Parse a ``start``/``end`` bound into an aware UTC datetime.

    Uses the same lenient rules as :func:`normalize_slot_bound`; failures
    raise the bare ``400 Bad Request`` message the live server answers with.
    """
    try:
        normalized = normalize_slot_bound(value, field=field)
    except ValueError:
        raise ValueError(f"API returned 400 Bad Request: {field}={value!r} is not a valid ISO date-time") from None
    try:
        parsed = _parse_candidate(normalized)
    except ValueError:
        raise ValueError(f"API returned 400 Bad Request: {field}={value!r} is not a valid ISO date-time") from None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
