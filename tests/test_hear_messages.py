import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_unread_messages = AsyncMock(return_value=[
        {"id": "msg1", "from_name": "Sarah", "content": "Hi grandma, call me tonight!", "created_at": None},
        {"id": "msg2", "from_name": "Mike", "content": "Happy birthday mom!", "created_at": None},
    ])
    db.mark_messages_read = AsyncMock()
    return db


@pytest.fixture
def mock_db_empty():
    db = AsyncMock()
    db.get_unread_messages = AsyncMock(return_value=[])
    db.mark_messages_read = AsyncMock()
    return db


@pytest.fixture
def metadata():
    return {
        "family_id": "smith_family",
        "member_id": "member_rose",
        "member_name": "Rose",
        "member_role": "grandparent",
        "is_device_user": True,
        "is_authorized": True,
    }


def test_hear_messages_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("hear_messages" in name for name in tool_names)


@pytest.mark.asyncio
async def test_hear_messages_returns_both_messages(mock_db):
    from tools.message_tools import make_hear_messages
    tool = make_hear_messages(mock_db, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "Sarah" in result
    assert "Mike" in result
    assert "Hi grandma" in result
    assert "Happy birthday" in result


@pytest.mark.asyncio
async def test_hear_messages_marks_as_read(mock_db):
    from tools.message_tools import make_hear_messages
    tool = make_hear_messages(mock_db, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx)
    mock_db.mark_messages_read.assert_called_once_with("smith_family", ["msg1", "msg2"])


@pytest.mark.asyncio
async def test_hear_messages_no_messages(mock_db_empty):
    from tools.message_tools import make_hear_messages
    tool = make_hear_messages(mock_db_empty, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "no new messages" in result.lower()


@pytest.mark.asyncio
async def test_hear_messages_does_not_mark_when_empty(mock_db_empty):
    from tools.message_tools import make_hear_messages
    tool = make_hear_messages(mock_db_empty, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    await tool.func(mock_ctx)
    mock_db_empty.mark_messages_read.assert_not_called()
