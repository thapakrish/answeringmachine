import pytest
import pytest_asyncio
from firebase_client import FirebaseClient


@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    yield client


@pytest_asyncio.fixture
async def seeded_db():
    """Fresh client + seed a test family, clean up after."""
    client = FirebaseClient()
    family_ref = client.db.collection("families").document("test_family")
    await family_ref.set({
        "name": "Test Family",
        "device_phones": ["+10000000001"],
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
    yield client
    # Cleanup
    await member_ref.delete()
    await member_ref2.delete()
    await family_ref.delete()


@pytest.mark.asyncio
async def test_find_family_by_device_phone_found(seeded_db):
    result = await seeded_db.find_family_by_device_phone("+10000000001")
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
