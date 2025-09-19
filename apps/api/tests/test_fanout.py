import os
import pytest
import asyncio

from src.services.fanout import publish_event, subscribe_events, _channel_for_interview


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="REDIS_URL not configured")
async def test_publish_and_subscribe_roundtrip() -> None:
    ch = _channel_for_interview(123456)
    async def _consumer():
        async for evt in subscribe_events(ch):
            if evt.get("event") == "ping" and evt.get("data", {}).get("x") == 1:
                return True
    consumer_task = asyncio.create_task(_consumer())
    # Give the subscriber a moment to subscribe before publish
    await asyncio.sleep(0.2)
    await publish_event(ch, "ping", {"x": 1})
    ok = await asyncio.wait_for(consumer_task, timeout=3.0)
    assert ok is True

