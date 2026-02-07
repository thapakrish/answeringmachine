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
        "member_id": "member_sarah",
        "member_name": "Sarah",
        "member_role": "granddaughter",
        "is_device_user": False,
        "is_authorized": True,
    }


@pytest.fixture
def guest_metadata():
    return {
        "family_id": "smith_family",
        "member_id": "guest",
        "member_name": "Guest",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": True,
        "is_guest": True,
    }


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


def test_agent_has_process_method(metadata, mock_db):
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    assert hasattr(agent, "process")
    assert callable(agent.process)


def test_agent_uses_haiku(metadata, mock_db):
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    assert "haiku" in agent.model_id.lower()


def test_agent_has_end_call_tool(metadata, mock_db):
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("end_call" in name for name in tool_names)
