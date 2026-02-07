# Task 02: FirebaseClient - Core Lookup Operations

- **Priority**: P0
- **Deps**: Task 00 (service account), Task 01 (scaffold)
- **PRD**: FR-5.1, FR-5.2, FR-1.1, FR-1.2, NFR-6

## Objective

Create `FirebaseClient` with async Firestore operations for family and member lookup.

## Tests First

```python
# tests/test_firebase_client.py
import pytest
import pytest_asyncio

# NOTE: Tests run against Firestore emulator or real Firestore.
# conftest.py should provide a `db` fixture that returns a FirebaseClient.

@pytest_asyncio.fixture
async def db():
    from firebase_client import FirebaseClient
    client = FirebaseClient()
    yield client

@pytest_asyncio.fixture
async def seeded_db(db):
    """Seed a test family, clean up after."""
    family_ref = db.db.collection("families").document("test_family")
    await family_ref.set({
        "name": "Test Family",
        "device_phones": ["+15551234567"],
        "passphrase": "test phrase",
    })
    member_ref = family_ref.collection("members").document("member_rose")
    await member_ref.set({
        "name": "Rose",
        "role": "grandparent",
        "phone_numbers": ["+15559876543"],
        "is_device_user": True,
        "preferences": {"interests": ["reading"]},
    })
    member_ref2 = family_ref.collection("members").document("member_sarah")
    await member_ref2.set({
        "name": "Sarah",
        "role": "granddaughter",
        "phone_numbers": ["+15551111111"],
        "is_device_user": False,
        "preferences": {},
    })
    yield db
    # Cleanup
    await member_ref.delete()
    await member_ref2.delete()
    await family_ref.delete()


@pytest.mark.asyncio
async def test_find_family_by_device_phone_found(seeded_db):
    result = await seeded_db.find_family_by_device_phone("+15551234567")
    assert result is not None
    assert result["name"] == "Test Family"
    assert result["id"] == "test_family"

@pytest.mark.asyncio
async def test_find_family_by_device_phone_not_found(seeded_db):
    result = await seeded_db.find_family_by_device_phone("+19999999999")
    assert result is None

@pytest.mark.asyncio
async def test_find_member_by_phone_found(seeded_db):
    result = await seeded_db.find_member_by_phone("test_family", "+15559876543")
    assert result is not None
    assert result["name"] == "Rose"

@pytest.mark.asyncio
async def test_find_member_by_phone_not_found(seeded_db):
    result = await seeded_db.find_member_by_phone("test_family", "+19999999999")
    assert result is None

@pytest.mark.asyncio
async def test_get_primary_device_user(seeded_db):
    result = await seeded_db.get_primary_device_user("test_family")
    assert result is not None
    assert result["name"] == "Rose"
    assert result["is_device_user"] is True

@pytest.mark.asyncio
async def test_get_passphrase(seeded_db):
    result = await seeded_db.get_passphrase("test_family")
    assert result == "test phrase"

@pytest.mark.asyncio
async def test_get_passphrase_no_family(seeded_db):
    result = await seeded_db.get_passphrase("nonexistent_family")
    assert result is None
```

## Implementation

```python
# firebase_client.py
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore_async
from loguru import logger


class FirebaseClient:
    def __init__(self):
        if not firebase_admin._apps:
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        # Use firebase_admin's async client, not the sync client.
        self.db = firestore_async.client()

    async def find_family_by_device_phone(self, phone: str) -> dict | None:
        """Find family by device phone number."""
        query = self.db.collection("families").where(
            "device_phones", "array_contains", phone
        )
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def find_member_by_phone(self, family_id: str, phone: str) -> dict | None:
        """Find member in family by phone number."""
        query = (self.db.collection("families").document(family_id)
                 .collection("members")
                 .where("phone_numbers", "array_contains", phone))
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def get_primary_device_user(self, family_id: str) -> dict | None:
        """Get the primary device user in a family."""
        query = (self.db.collection("families").document(family_id)
                 .collection("members")
                 .where("is_device_user", "==", True))
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def get_passphrase(self, family_id: str) -> str | None:
        """Get family passphrase (field on family document)."""
        doc = await self.db.collection("families").document(family_id).get()
        if doc.exists:
            return doc.to_dict().get("passphrase")
        return None
```

## Verification

```bash
pytest tests/test_firebase_client.py -v
```
