import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallEnded, UserTextSent
import litellm


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
async def test_call_ended_saves_memory(metadata, mock_db, monkeypatch):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    agent._input_history.append(UserTextSent(content="Let's talk about gardening"))

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = '{"summary": "Discussed gardening and upcoming doctor appointment", "topics": ["gardening", "health"], "mood": "content"}'
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=mock_response))

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    mock_db.save_memory.assert_called_once()
    call_kwargs = mock_db.save_memory.call_args
    assert call_kwargs[0][0] == "smith_family"
    assert call_kwargs[0][1] == "member_rose"
    assert call_kwargs[1]["summary"] == "Discussed gardening and upcoming doctor appointment"
    assert call_kwargs[1]["topics"] == ["gardening", "health"]
    assert call_kwargs[1]["mood"] == "content"
    assert "gardening" in call_kwargs[1]["transcript"]


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
async def test_call_ended_no_history_skips_save(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    mock_db.save_memory.assert_not_called()


@pytest.mark.asyncio
async def test_call_ended_strips_markdown_fences(metadata, mock_db, monkeypatch):
    """DeviceUserAgent handles LLM responses wrapped in markdown code fences."""
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    agent._input_history.append(UserTextSent(content="What's the weather like?"))

    fenced = '```json\n{"summary": "Asked about the weather.", "topics": ["weather"], "mood": "curious"}\n```'
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = fenced
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=mock_response))

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    mock_db.save_memory.assert_called_once()
    assert mock_db.save_memory.call_args[1]["summary"] == "Asked about the weather."
