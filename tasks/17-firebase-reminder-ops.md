# Task 17: FirebaseClient - Reminder Operations

- **Priority**: P1
- **Deps**: Task 02
- **PRD**: FR-5.4

## Objective

Add reminder operations to `FirebaseClient`: save reminders and fetch active reminders for a member.

## Tests First

```python
# tests/test_firebase_reminder_ops.py
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
    rems = client.db.collection("families").document("test_family").collection("reminders")
    async for doc in rems.stream():
        await doc.reference.delete()
    await client.db.collection("families").document("test_family").delete()


@pytest.mark.asyncio
async def test_save_reminder(db):
    rem_id = await db.save_reminder(
        family_id="test_family",
        for_member_id="member_rose",
        created_by_id="member_sarah",
        content="Take medicine at 9am",
        time_str="9:00 AM",
        recurring=True,
    )
    assert rem_id is not None

@pytest.mark.asyncio
async def test_get_reminders(db):
    await db.save_reminder("test_family", "member_rose", "member_sarah", "Take medicine", "9:00 AM", True)
    await db.save_reminder("test_family", "member_rose", "member_mike", "Doctor appointment", "2:00 PM", False)
    reminders = await db.get_reminders("test_family", "member_rose")
    assert len(reminders) == 2

@pytest.mark.asyncio
async def test_get_reminders_only_active(db):
    rem_id = await db.save_reminder("test_family", "member_rose", "member_sarah", "Old reminder", "8:00 AM", False)
    # Deactivate
    await db.db.collection("families").document("test_family").collection("reminders").document(rem_id).update({"active": False})
    await db.save_reminder("test_family", "member_rose", "member_mike", "Active reminder", "10:00 AM", False)
    reminders = await db.get_reminders("test_family", "member_rose")
    assert len(reminders) == 1
    assert reminders[0]["content"] == "Active reminder"

@pytest.mark.asyncio
async def test_get_reminders_filters_by_member(db):
    await db.save_reminder("test_family", "member_rose", "member_sarah", "Rose's reminder", "9:00 AM", False)
    await db.save_reminder("test_family", "member_sarah", "member_rose", "Sarah's reminder", "10:00 AM", False)
    reminders = await db.get_reminders("test_family", "member_rose")
    assert len(reminders) == 1
    assert reminders[0]["content"] == "Rose's reminder"

@pytest.mark.asyncio
async def test_saved_reminder_has_required_fields(db):
    rem_id = await db.save_reminder("test_family", "member_rose", "member_sarah", "Take pills", "9:00 AM", True)
    doc = await db.db.collection("families").document("test_family").collection("reminders").document(rem_id).get()
    data = doc.to_dict()
    assert data["for_member_id"] == "member_rose"
    assert data["created_by_member_id"] == "member_sarah"
    assert data["content"] == "Take pills"
    assert data["time"] == "9:00 AM"
    assert data["recurring"] is True
    assert data["active"] is True
```

## Implementation

```python
# firebase_client.py (additions)

async def save_reminder(self, family_id, for_member_id, created_by_id, content, time_str, recurring):
    ref = self.db.collection("families").document(family_id).collection("reminders").document()
    await ref.set({
        "for_member_id": for_member_id,
        "created_by_member_id": created_by_id,
        "content": content,
        "time": time_str,
        "recurring": recurring,
        "active": True,
        "created_at": SERVER_TIMESTAMP,
    })
    return ref.id

async def get_reminders(self, family_id, member_id):
    refs = (
        self.db.collection("families").document(family_id).collection("reminders")
        .where("for_member_id", "==", member_id)
        .where("active", "==", True)
    )
    return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]
```

## Verification

```bash
pytest tests/test_firebase_reminder_ops.py -v
```
