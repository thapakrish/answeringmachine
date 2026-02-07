# Task 13: FirebaseClient - Memory Operations

- **Priority**: P1
- **Deps**: Task 02
- **PRD**: FR-5.5

## Objective

Add memory operations to `FirebaseClient`: get conversation memory for a member and save new conversation summaries. Memory is stored per-member and capped at 20 entries.

## Tests First

```python
# tests/test_firebase_memory_ops.py
import pytest
import pytest_asyncio
from firebase_client import FirebaseClient

@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    await client.db.collection("families").document("test_family").set({
        "name": "Test Family",
    })
    yield client
    # Cleanup
    mem_ref = client.db.collection("families").document("test_family").collection("memory").document("member_test")
    await mem_ref.delete()
    await client.db.collection("families").document("test_family").delete()


@pytest.mark.asyncio
async def test_get_memory_exists(db):
    mem_ref = db.db.collection("families").document("test_family").collection("memory").document("member_test")
    await mem_ref.set({
        "recent_conversations": [{"date": "2025-01-01", "summary": "Talked about books", "topics": ["books"], "mood": "happy"}],
        "preferences": {"interests": ["reading"]},
        "last_interaction": "2025-01-01",
    })
    result = await db.get_memory("test_family", "member_test")
    assert len(result["recent_conversations"]) == 1
    assert result["recent_conversations"][0]["summary"] == "Talked about books"

@pytest.mark.asyncio
async def test_get_memory_not_exists(db):
    result = await db.get_memory("test_family", "nonexistent_member")
    assert result["recent_conversations"] == []
    assert result["preferences"] == {}

@pytest.mark.asyncio
async def test_save_memory_creates_doc(db):
    await db.save_memory("test_family", "member_test", summary="Discussed gardening", topics=["gardening"], mood="content")
    doc = await db.db.collection("families").document("test_family").collection("memory").document("member_test").get()
    assert doc.exists
    data = doc.to_dict()
    assert len(data["recent_conversations"]) == 1
    assert data["recent_conversations"][0]["summary"] == "Discussed gardening"

@pytest.mark.asyncio
async def test_save_memory_appends_conversation(db):
    await db.save_memory("test_family", "member_test", summary="First chat", topics=["weather"], mood="neutral")
    await db.save_memory("test_family", "member_test", summary="Second chat", topics=["books"], mood="happy")
    result = await db.get_memory("test_family", "member_test")
    assert len(result["recent_conversations"]) == 2

@pytest.mark.asyncio
async def test_save_memory_caps_at_20(db):
    for i in range(25):
        await db.save_memory("test_family", "member_test", summary=f"Chat {i}", topics=["test"], mood="neutral")
    result = await db.get_memory("test_family", "member_test")
    assert len(result["recent_conversations"]) == 20
    # Should keep the most recent 20
    assert result["recent_conversations"][-1]["summary"] == "Chat 24"

@pytest.mark.asyncio
async def test_save_memory_updates_last_interaction(db):
    await db.save_memory("test_family", "member_test", summary="Chat", topics=[], mood="neutral")
    result = await db.get_memory("test_family", "member_test")
    assert "last_interaction" in result
```

## Implementation

```python
# firebase_client.py (additions)
from datetime import datetime

async def get_memory(self, family_id, member_id):
    doc = await (
        self.db.collection("families").document(family_id)
        .collection("memory").document(member_id).get()
    )
    if not doc.exists:
        return {"recent_conversations": [], "preferences": {}, "last_interaction": None}
    return doc.to_dict()

async def save_memory(self, family_id, member_id, summary, topics, mood):
    ref = self.db.collection("families").document(family_id).collection("memory").document(member_id)
    doc = await ref.get()

    now = datetime.utcnow().isoformat()
    entry = {"date": now, "summary": summary, "topics": topics, "mood": mood}

    if doc.exists:
        data = doc.to_dict()
        convos = data.get("recent_conversations", [])
        convos.append(entry)
        convos = convos[-20:]  # Keep only last 20
        await ref.update({
            "recent_conversations": convos,
            "last_interaction": now,
        })
    else:
        await ref.set({
            "recent_conversations": [entry],
            "preferences": {},
            "last_interaction": now,
        })
```

## Verification

```bash
pytest tests/test_firebase_memory_ops.py -v
```
