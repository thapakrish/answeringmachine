import pytest
import pytest_asyncio
from firebase_client import FirebaseClient


@pytest_asyncio.fixture
async def db():
    client = FirebaseClient()
    await client.db.collection("families").document("test_msg_family").set({
        "name": "Test Family",
        "device_phones": ["+10000000002"],
    })
    yield client
    # Cleanup messages
    msgs = client.db.collection("families").document("test_msg_family").collection("messages")
    async for doc in msgs.stream():
        await doc.reference.delete()
    await client.db.collection("families").document("test_msg_family").delete()


@pytest.mark.asyncio
async def test_save_message(db):
    msg_id = await db.save_message(
        family_id="test_msg_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    assert msg_id is not None


@pytest.mark.asyncio
async def test_saved_message_defaults_unread(db):
    msg_id = await db.save_message(
        family_id="test_msg_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    doc = await db.db.collection("families").document("test_msg_family").collection("messages").document(msg_id).get()
    assert doc.to_dict()["read"] is False


@pytest.mark.asyncio
async def test_saved_message_has_timestamp(db):
    msg_id = await db.save_message(
        family_id="test_msg_family",
        from_member_id="member_sarah",
        from_name="Sarah",
        to_member_id="member_rose",
        content="Hi grandma!",
    )
    doc = await db.db.collection("families").document("test_msg_family").collection("messages").document(msg_id).get()
    assert "created_at" in doc.to_dict()


@pytest.mark.asyncio
async def test_get_unread_messages(db):
    await db.save_message("test_msg_family", "member_sarah", "Sarah", "member_rose", "Message 1")
    await db.save_message("test_msg_family", "member_mike", "Mike", "member_rose", "Message 2")
    msgs = await db.get_unread_messages("test_msg_family", "member_rose")
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_get_unread_messages_excludes_read(db):
    msg_id = await db.save_message("test_msg_family", "member_sarah", "Sarah", "member_rose", "Old message")
    await db.mark_messages_read("test_msg_family", [msg_id])
    await db.save_message("test_msg_family", "member_mike", "Mike", "member_rose", "New message")
    msgs = await db.get_unread_messages("test_msg_family", "member_rose")
    assert len(msgs) == 1
    assert msgs[0]["from_name"] == "Mike"


@pytest.mark.asyncio
async def test_get_unread_messages_empty(db):
    msgs = await db.get_unread_messages("test_msg_family", "member_rose")
    assert msgs == []


@pytest.mark.asyncio
async def test_mark_messages_read(db):
    msg_id = await db.save_message("test_msg_family", "member_sarah", "Sarah", "member_rose", "Read me")
    await db.mark_messages_read("test_msg_family", [msg_id])
    doc = await db.db.collection("families").document("test_msg_family").collection("messages").document(msg_id).get()
    assert doc.to_dict()["read"] is True
