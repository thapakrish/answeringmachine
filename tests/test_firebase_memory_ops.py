import pytest
import pytest_asyncio
from firebase_client import FirebaseClient


@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    await client.db.collection("families").document("test_mem_family").set({
        "name": "Test Family",
    })
    yield client
    # Cleanup
    mem_ref = client.db.collection("families").document("test_mem_family").collection("memory").document("member_test")
    await mem_ref.delete()
    await client.db.collection("families").document("test_mem_family").delete()


@pytest.mark.asyncio
async def test_get_memory_exists(db):
    mem_ref = db.db.collection("families").document("test_mem_family").collection("memory").document("member_test")
    await mem_ref.set({
        "recent_conversations": [{"date": "2025-01-01", "summary": "Talked about books", "topics": ["books"], "mood": "happy"}],
        "preferences": {"interests": ["reading"]},
        "last_interaction": "2025-01-01",
    })
    result = await db.get_memory("test_mem_family", "member_test")
    assert len(result["recent_conversations"]) == 1
    assert result["recent_conversations"][0]["summary"] == "Talked about books"


@pytest.mark.asyncio
async def test_get_memory_not_exists(db):
    result = await db.get_memory("test_mem_family", "nonexistent_member")
    assert result["recent_conversations"] == []
    assert result["preferences"] == {}


@pytest.mark.asyncio
async def test_save_memory_creates_doc(db):
    await db.save_memory("test_mem_family", "member_test", summary="Discussed gardening", topics=["gardening"], mood="content")
    doc = await db.db.collection("families").document("test_mem_family").collection("memory").document("member_test").get()
    assert doc.exists
    data = doc.to_dict()
    assert len(data["recent_conversations"]) == 1
    assert data["recent_conversations"][0]["summary"] == "Discussed gardening"


@pytest.mark.asyncio
async def test_save_memory_appends_conversation(db):
    await db.save_memory("test_mem_family", "member_test", summary="First chat", topics=["weather"], mood="neutral")
    await db.save_memory("test_mem_family", "member_test", summary="Second chat", topics=["books"], mood="happy")
    result = await db.get_memory("test_mem_family", "member_test")
    assert len(result["recent_conversations"]) == 2


@pytest.mark.asyncio
async def test_save_memory_caps_at_20(db):
    for i in range(25):
        await db.save_memory("test_mem_family", "member_test", summary=f"Chat {i}", topics=["test"], mood="neutral")
    result = await db.get_memory("test_mem_family", "member_test")
    assert len(result["recent_conversations"]) == 20
    assert result["recent_conversations"][-1]["summary"] == "Chat 24"


@pytest.mark.asyncio
async def test_save_memory_updates_last_interaction(db):
    await db.save_memory("test_mem_family", "member_test", summary="Chat", topics=[], mood="neutral")
    result = await db.get_memory("test_mem_family", "member_test")
    assert "last_interaction" in result
