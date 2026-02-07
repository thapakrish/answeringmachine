import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_message = AsyncMock(return_value="msg_123")
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


@pytest.fixture
def metadata():
    return {
        "family_id": "smith_family",
        "member_id": "member_sarah",
        "member_name": "Sarah",
        "member_role": "granddaughter",
        "is_device_user": False,
        "is_authorized": True,
    }


def test_leave_message_tool_on_agent(metadata, mock_db):
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("leave_message" in name for name in tool_names)


@pytest.mark.asyncio
async def test_leave_message_saves_to_firestore(mock_db):
    from tools.message_tools import make_leave_message
    tool = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, message_content="Tell grandma I'll visit Sunday")
    mock_db.save_message.assert_called_once()
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["content"] == "Tell grandma I'll visit Sunday"
    assert call_args.kwargs["from_member_id"] == "member_sarah"
    assert call_args.kwargs["from_name"] == "Sarah"


@pytest.mark.asyncio
async def test_leave_message_targets_device_user(mock_db):
    from tools.message_tools import make_leave_message
    tool = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx, message_content="Hello grandma")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["to_member_id"] == "member_rose"


@pytest.mark.asyncio
async def test_leave_message_returns_confirmation(mock_db):
    from tools.message_tools import make_leave_message
    tool = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, message_content="See you Sunday")
    assert "message" in result.lower()
    assert "delivered" in result.lower() or "saved" in result.lower() or "left" in result.lower()
