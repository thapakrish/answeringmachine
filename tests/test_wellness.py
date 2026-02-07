import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [
            {"date": "2025-01-15", "summary": "Talked about gardening", "topics": ["gardening"], "mood": "happy"},
            {"date": "2025-01-14", "summary": "Discussed doctor visit", "topics": ["health"], "mood": "anxious"},
        ],
        "preferences": {},
        "last_interaction": "2025-01-15T10:30:00",
    })
    db.get_recent_call_logs = AsyncMock(return_value=[
        {"timestamp": "2025-01-15T10:30:00", "caller_name": "Rose", "summary": "Chatted about garden"},
        {"timestamp": "2025-01-14T09:00:00", "caller_name": "Rose", "summary": "Asked about weather"},
    ])
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


@pytest.mark.asyncio
async def test_check_wellness_returns_activity(mock_db):
    from tools.wellness_tools import make_check_wellness
    tool = make_check_wellness(mock_db, "smith_family")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "2025-01-15" in result
    assert "doctor" in result.lower() or "health" in result.lower()


@pytest.mark.asyncio
async def test_check_wellness_returns_mood(mock_db):
    from tools.wellness_tools import make_check_wellness
    tool = make_check_wellness(mock_db, "smith_family")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "happy" in result.lower() or "mood" in result.lower()


def test_check_wellness_not_available_for_guests():
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
    assert not any("check_wellness" in name for name in tool_names)


def test_check_wellness_available_for_family_member():
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
    assert any("check_wellness" in name for name in tool_names)
