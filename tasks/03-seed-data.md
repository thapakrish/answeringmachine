# Task 03: Seed Data Script

- **Priority**: P0
- **Deps**: Task 02
- **PRD**: FR-5.1, FR-5.2

## Objective

Create a script to populate Firestore with the demo Smith family. Must be idempotent.

## Tests First

```python
# tests/test_seed_data.py
import pytest
import pytest_asyncio
from firebase_client import FirebaseClient

@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    yield client

@pytest.mark.asyncio
async def test_seed_creates_family(db):
    from seed_data import seed
    await seed()
    family = await db.find_family_by_device_phone("+15551234567")
    assert family is not None
    assert family["name"] == "The Smiths"
    assert "+15551234567" in family["device_phones"]
    assert family.get("passphrase") is not None

@pytest.mark.asyncio
async def test_seed_creates_four_members(db):
    from seed_data import seed
    await seed()
    members_ref = db.db.collection("families").document("smith_family").collection("members")
    docs = [doc async for doc in members_ref.stream()]
    assert len(docs) == 4
    names = {doc.to_dict()["name"] for doc in docs}
    assert names == {"Rose", "Sarah", "Mike", "Emma"}

@pytest.mark.asyncio
async def test_seed_creates_messages(db):
    from seed_data import seed
    await seed()
    msgs_ref = db.db.collection("families").document("smith_family").collection("messages")
    docs = [doc async for doc in msgs_ref.stream()]
    assert len(docs) >= 2

@pytest.mark.asyncio
async def test_seed_creates_reminders(db):
    from seed_data import seed
    await seed()
    rems_ref = db.db.collection("families").document("smith_family").collection("reminders")
    docs = [doc async for doc in rems_ref.stream()]
    assert len(docs) >= 2

@pytest.mark.asyncio
async def test_seed_creates_memory(db):
    from seed_data import seed
    await seed()
    mem_ref = db.db.collection("families").document("smith_family").collection("memory").document("member_rose")
    doc = await mem_ref.get()
    assert doc.exists
    data = doc.to_dict()
    assert "recent_conversations" in data
    assert len(data["recent_conversations"]) > 0

@pytest.mark.asyncio
async def test_seed_is_idempotent(db):
    from seed_data import seed
    await seed()
    await seed()  # Run twice
    members_ref = db.db.collection("families").document("smith_family").collection("members")
    docs = [doc async for doc in members_ref.stream()]
    assert len(docs) == 4  # No duplicates
```

## Implementation

```python
# seed_data.py
"""Seed Firestore with demo Smith family. Idempotent: uses fixed document IDs."""

FAMILY_ID = "smith_family"
MEMBERS = {
    "member_rose": {"name": "Rose", "role": "grandparent", "phone_numbers": ["+15551234567"], "is_device_user": True, "preferences": {"interests": ["mystery novels", "gardening"]}},
    "member_sarah": {"name": "Sarah", "role": "granddaughter", "phone_numbers": ["+15559876543"], "is_device_user": False, "preferences": {}},
    "member_mike": {"name": "Mike", "role": "son", "phone_numbers": ["+15551111111"], "is_device_user": False, "preferences": {}},
    "member_emma": {"name": "Emma", "role": "great-granddaughter", "phone_numbers": ["+15552222222"], "is_device_user": False, "preferences": {}},
}
# ... (messages, reminders, memory)
```

Idempotency via fixed document IDs and `set()` (upsert).

## Verification

```bash
pytest tests/test_seed_data.py -v
python seed_data.py  # Visual check in Firebase Console
```
