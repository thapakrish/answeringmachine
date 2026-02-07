# Task 08: FirebaseClient - Message Operations

- **Priority**: P0
- **Deps**: Task 02
- **PRD**: FR-5.3

## Objective

Add message operations to `FirebaseClient`: save messages, fetch unread messages, and mark messages as read.

## Tests First

```python
# tests/test_firebase_message_ops.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from firebase_client import FirebaseClient

@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    # Seed a family for testing
    await client.db.collection("families").document("test_family").set({
        "name": "Test Family",
        "device_phones": ["+10000000000"],
    })
    yield client
    # Cleanup
    msgs = client.db.collection("families").document("test_family").collection("messages")
    async for doc in msgs.stream():
        await doc.reference.delete()
    await client.db.collection("families").document("test_family").delete()


@pytest.mark.asyncio
async def test_save_message(db):
    msg_id = await db.save_message(
        family_id="test_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    assert msg_id is not None

@pytest.mark.asyncio
async def test_saved_message_defaults_unread(db):
    msg_id = await db.save_message(
        family_id="test_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    doc = await db.db.collection("families").document("test_family").collection("messages").document(msg_id).get()
    assert doc.to_dict()["read"] is False

@pytest.mark.asyncio
async def test_saved_message_has_timestamp(db):
    msg_id = await db.save_message(
        family_id="test_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    doc = await db.db.collection("families").document("test_family").collection("messages").document(msg_id).get()
    assert "created_at" in doc.to_dict()

@pytest.mark.asyncio
async def test_get_unread_messages(db):
    await db.save_message("test_family", "member_sarah", "Sarah", "member_rose", "Message 1")
    await db.save_message("test_family", "member_mike", "Mike", "member_rose", "Message 2")
    msgs = await db.get_unread_messages("test_family", "member_rose")
    assert len(msgs) == 2

@pytest.mark.asyncio
async def test_get_unread_messages_excludes_read(db):
    msg_id = await db.save_message("test_family", "member_sarah", "Sarah", "member_rose", "Old message")
    await db.mark_messages_read("test_family", [msg_id])
    await db.save_message("test_family", "member_mike", "Mike", "member_rose", "New message")
    msgs = await db.get_unread_messages("test_family", "member_rose")
    assert len(msgs) == 1
    assert msgs[0]["from_name"] == "Mike"

@pytest.mark.asyncio
async def test_get_unread_messages_empty(db):
    msgs = await db.get_unread_messages("test_family", "member_rose")
    assert msgs == []

@pytest.mark.asyncio
async def test_mark_messages_read(db):
    msg_id = await db.save_message("test_family", "member_sarah", "Sarah", "member_rose", "Read me")
    await db.mark_messages_read("test_family", [msg_id])
    doc = await db.db.collection("families").document("test_family").collection("messages").document(msg_id).get()
    assert doc.to_dict()["read"] is True
```

## Implementation

```python
# firebase_client.py (additions)
from google.cloud.firestore import SERVER_TIMESTAMP

async def save_message(self, family_id, from_member_id, from_name, to_member_id, content):
    ref = self.db.collection("families").document(family_id).collection("messages").document()
    await ref.set({
        "from_member_id": from_member_id,
        "from_name": from_name,
        "to_member_id": to_member_id,
        "content": content,
        "read": False,
        "created_at": SERVER_TIMESTAMP,
    })
    return ref.id

async def get_unread_messages(self, family_id, member_id):
    msgs_ref = (
        self.db.collection("families").document(family_id).collection("messages")
        .where("to_member_id", "==", member_id)
        .where("read", "==", False)
        .order_by("created_at")
    )
    return [{"id": doc.id, **doc.to_dict()} async for doc in msgs_ref.stream()]

async def mark_messages_read(self, family_id, message_ids):
    for msg_id in message_ids:
        ref = self.db.collection("families").document(family_id).collection("messages").document(msg_id)
        await ref.update({"read": True})
```

## Verification

```bash
pytest tests/test_firebase_message_ops.py -v
```
