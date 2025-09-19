import os
import pytest
import json

from src.services.ephemeral_store import store as eph


@pytest.mark.asyncio
async def test_ephemeral_store_put_get_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure it works without Redis as well
    key = f"eph:test:{eph.new_id()}"
    data = {"a": 1, "b": "x"}
    await eph.put(key, data, ttl_seconds=1)
    got = await eph.get(key)
    assert got and got.get("a") == 1 and got.get("b") == "x"
    await eph.delete(key)
    gone = await eph.get(key)
    assert gone is None

