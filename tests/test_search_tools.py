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
    db.get_memory = AsyncMock(return_value={"recent_conversations": [], "preferences": {}})
    db.get_unread_messages = AsyncMock(return_value=[])
    return db


def test_web_search_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("web_search" in name or "search" in name for name in tool_names)


def test_browse_website_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("browse_website" in name for name in tool_names)
