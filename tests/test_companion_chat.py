import os
import pytest
from unittest.mock import AsyncMock


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
def mock_db():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [],
        "preferences": {"interests": ["mystery novels", "gardening"]},
    })
    db.get_unread_messages = AsyncMock(return_value=[])
    return db


def test_companion_agent_exists(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    assert hasattr(agent, "_companion")
    assert agent._companion is not None


def test_companion_handoff_tool_exists(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("companion" in name.lower() for name in tool_names)


def test_companion_has_end_call(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._companion._tools]
    assert any("end_call" in name for name in tool_names)
