"""Tests for release-1.111.4: lenient slot normalizer, promotions fix, slots total."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from silpo_py_mcp import SilpoClient
from silpo_py_mcp.slot_time import normalize_slot_bound, parse_slot_bound, strip_millis
from silpo_py_mcp.tools import SilpoTool


def test_strip_millis_handles_dot_and_comma() -> None:
    assert strip_millis("2026-09-02T10:00:00.123Z") == "2026-09-02T10:00:00Z"
    assert strip_millis("2026-09-02T10:00:00,123Z") == "2026-09-02T10:00:00Z"
    assert strip_millis("2026-09-02T10:00:00.123+00:00") == "2026-09-02T10:00:00+00:00"
    assert strip_millis("2026-09-02T10:00:00") == "2026-09-02T10:00:00"


def test_normalize_slot_bound_is_lenient() -> None:
    assert normalize_slot_bound(" 2026-09-02T10:00:00Z ", field="start") == "2026-09-02T10:00:00Z"
    assert normalize_slot_bound("2026-09-02T10:00:00z", field="start") == "2026-09-02T10:00:00Z"
    assert normalize_slot_bound("2026-09-02T10:00:00,123z", field="start") == "2026-09-02T10:00:00Z"
    assert normalize_slot_bound("2026-09-02T10:00:00+0000", field="start") == "2026-09-02T10:00:00+00:00"
    assert normalize_slot_bound("2026-09-02T10:00:00+00", field="start") == "2026-09-02T10:00:00+00:00"
    assert normalize_slot_bound("2026-09-02 10:00:00+00:00", field="start") == "2026-09-02 10:00:00+00:00"
    assert normalize_slot_bound("2026-09-02T08:00:00.123Z", field="start") == "2026-09-02T08:00:00Z"
    assert normalize_slot_bound("2026-09-02T10:00:00", field="start") == "2026-09-02T10:00:00"


def test_normalize_slot_bound_rejects_date_only() -> None:
    for bad in ("2026-09-02", "garbage", ""):
        with pytest.raises(ValueError, match="not a valid ISO date-time"):
            normalize_slot_bound(bad, field="start")


def test_parse_slot_bound_reads_all_forms_as_utc() -> None:
    zulu = parse_slot_bound("2026-09-02T08:00:00Z", "start")
    naive = parse_slot_bound("2026-09-02T08:00:00", "start")
    offset = parse_slot_bound("2026-09-02T08:00:00+00:00", "start")
    compact = parse_slot_bound("2026-09-02T08:00:00+0000", "start")
    assert (zulu, naive, offset, compact) is not None
    assert zulu == naive == offset == compact
    assert zulu.tzinfo is not None


def test_parse_slot_bound_rejects_with_400_message() -> None:
    with pytest.raises(ValueError, match="400 Bad Request"):
        parse_slot_bound("2026-09-02", "start")


async def test_get_time_slots_accepts_lenient_bounds(client: SilpoClient) -> None:
    slots = await client.get_time_slots(
        "bran-1",
        delivery_type="SelfPickup",
        start=" 2026-09-02T08:00:00,123z ",
        end="2026-09-02 09:00:00+0000",
    )
    assert [s.id for s in slots] == ["slot-0"]


async def test_get_time_slots_unwraps_total_envelope(client: SilpoClient) -> None:
    real_call_tool = client.call_tool

    async def fake(name: SilpoTool | str, arguments: Mapping[str, Any]) -> Any:
        assert str(name) == "silpo_get_time_slots"
        payload = await real_call_tool(name, arguments)
        items = payload if isinstance(payload, list) else payload.get("slots", [])
        return {"success": True, "summary": "3 slots", "slots": items, "total": len(items)}

    client.call_tool = fake  # type: ignore[method-assign]
    slots = await client.get_time_slots("bran-1", delivery_type="SelfPickup")
    assert len(slots) == 3


async def test_get_promotions_unknown_branch_returns_empty(client: SilpoClient) -> None:
    assert await client.get_promotions(
        "bran-1", "DeliveryHome", "2026-09-06T10:00:00+03:00", "2026-09-06T11:00:00+03:00"
    )
    assert (
        await client.get_promotions(
            "bran-does-not-exist", "DeliveryHome", "2026-09-06T10:00:00+03:00", "2026-09-06T11:00:00+03:00"
        )
        == []
    )
