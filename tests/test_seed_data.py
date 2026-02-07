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
