import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_message = AsyncMock(return_value="msg_anon_1")
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


@pytest.mark.asyncio
async def test_leave_anonymous_from_name(mock_db):
    from tools.message_tools import make_leave_anonymous
    tool = make_leave_anonymous(mock_db, "smith_family")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx, message_content="Happy birthday surprise coming!")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["from_name"] == "A family member"


@pytest.mark.asyncio
async def test_leave_anonymous_from_id(mock_db):
    from tools.message_tools import make_leave_anonymous
    tool = make_leave_anonymous(mock_db, "smith_family")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx, message_content="Check the garden")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["from_member_id"] == "anonymous"


@pytest.mark.asyncio
async def test_leave_anonymous_content_saved(mock_db):
    from tools.message_tools import make_leave_anonymous
    tool = make_leave_anonymous(mock_db, "smith_family")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx, message_content="There's a surprise in the mail")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["content"] == "There's a surprise in the mail"


@pytest.mark.asyncio
async def test_leave_anonymous_targets_device_user(mock_db):
    from tools.message_tools import make_leave_anonymous
    tool = make_leave_anonymous(mock_db, "smith_family")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx, message_content="Secret message")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["to_member_id"] == "member_rose"


@pytest.mark.asyncio
async def test_leave_anonymous_returns_confirmation(mock_db):
    from tools.message_tools import make_leave_anonymous
    tool = make_leave_anonymous(mock_db, "smith_family")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, message_content="Surprise!")
    assert "anonymous" in result.lower() or "family member" in result.lower()


def test_guest_does_not_have_leave_anonymous():
    from agents.family_member_agent import FamilyMemberAgent
    mock_db = AsyncMock()
    mock_db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    guest_metadata = {
        "family_id": "smith_family",
        "member_id": "guest",
        "member_name": "Guest",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": True,
        "is_guest": True,
    }
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert not any("leave_anonymous" in name for name in tool_names)


def test_normal_member_has_leave_anonymous():
    from agents.family_member_agent import FamilyMemberAgent
    mock_db = AsyncMock()
    mock_db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    metadata = {
        "family_id": "smith_family",
        "member_id": "member_sarah",
        "member_name": "Sarah",
        "member_role": "granddaughter",
        "is_device_user": False,
        "is_authorized": True,
    }
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("leave_anonymous" in name for name in tool_names)
