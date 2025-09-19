import pytest
import asyncio
from typing import List, Dict

from src.services.memory_enricher import enrich_session_memory
from src.services.memory_store import store as session_memory


@pytest.mark.asyncio
async def test_memory_enrichment_updates_summary_and_facts() -> None:
    interview_id = 9999
    history: List[Dict[str, str]] = [
        {"role": "assistant", "text": "Son projede hangi teknolojileri kullandınız?"},
        {"role": "user", "text": "Python ve React ile docker kullanarak mikroservis mimarisi geliştirdim."},
        {"role": "assistant", "text": "Performans optimizasyonu yaptınız mı?"},
        {"role": "user", "text": "Evet, Redis caching ve PostgreSQL indexler ekledim."},
    ]

    await enrich_session_memory(interview_id, history)

    snap = session_memory.snapshot(interview_id)
    assert snap["rolling_summary"]
    facts = snap["facts"]
    assert "mentioned_technologies" in facts
    mt = facts["mentioned_technologies"].lower()
    assert "python" in mt and "react" in mt and "docker" in mt and "redis" in mt
    assert facts.get("last_question", "").startswith("Performans")


