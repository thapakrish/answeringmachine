import os
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


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


@pytest.fixture
def mock_db_with_data():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [
            {"date": "2025-01-01", "summary": "Rose talked about finishing a mystery novel", "topics": ["mystery novels"], "mood": "happy"},
        ],
        "preferences": {"interests": ["mystery novels", "gardening"]},
        "last_interaction": "2025-01-01",
    })
    db.get_unread_messages = AsyncMock(return_value=[
        {"id": "msg1", "from_name": "Sarah", "content": "Hi grandma"},
        {"id": "msg2", "from_name": "Mike", "content": "Hello mom"},
        {"id": "msg3", "from_name": "Emma", "content": "Hi great-grandma"},
    ])
    return db


@pytest.fixture
def mock_db_empty():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={"recent_conversations": [], "preferences": {}})
    db.get_unread_messages = AsyncMock(return_value=[])
    return db


@pytest.mark.asyncio
async def test_greeting_includes_morning(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "good morning" in greeting.lower()


@pytest.mark.asyncio
async def test_greeting_includes_evening(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 19, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "good evening" in greeting.lower()


@pytest.mark.asyncio
async def test_greeting_includes_unread_count(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "3" in greeting
    assert "message" in greeting.lower()


@pytest.mark.asyncio
async def test_greeting_includes_memory(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "mystery novel" in greeting.lower()


@pytest.mark.asyncio
async def test_greeting_no_memory_still_works(metadata, mock_db_empty):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_empty)
    assert metadata["member_name"] in greeting


@pytest.mark.asyncio
async def test_greeting_no_messages_no_mention(metadata, mock_db_empty):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_empty)
    assert "0 " not in greeting
