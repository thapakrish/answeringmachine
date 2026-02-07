import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallEnded


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
    db.save_memory = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_call_ended_saves_memory(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    agent._conversation_summary = "Discussed gardening and upcoming doctor appointment"
    agent._conversation_topics = ["gardening", "health"]
    agent._conversation_mood = "content"

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    mock_db.save_memory.assert_called_once_with(
        "smith_family",
        "member_rose",
        summary="Discussed gardening and upcoming doctor appointment",
        topics=["gardening", "health"],
        mood="content",
    )


@pytest.mark.asyncio
async def test_call_ended_cleans_up(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    agent._greeter.cleanup = AsyncMock()
    agent._companion.cleanup = AsyncMock()

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    agent._greeter.cleanup.assert_called_once()
    agent._companion.cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_call_ended_no_summary_skips_save(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    mock_db.save_memory.assert_not_called()
