import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallEnded, CallStarted, UserTextSent, AgentSendText
import litellm


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
        "caller_phone": "+15551234567",
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
    db.save_memory = AsyncMock()
    db.log_call = AsyncMock()
    return db


def _mock_llm_response(content):
    """Helper to create a mock litellm response."""
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = content
    return mock_response


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


# --- CallEnded memory/logging tests ---

@pytest.mark.asyncio
async def test_call_ended_saves_memory_and_log(metadata, mock_db, monkeypatch):
    """On CallEnded with conversation history, both save_memory and log_call are called."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    agent._input_history.append(UserTextSent(content="Tell Rose I said happy birthday"))

    json_response = '{"summary": "Sarah called to wish Rose a happy birthday.", "topics": ["birthday", "greeting"], "mood": "happy"}'
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=_mock_llm_response(json_response)))

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    mock_db.log_call.assert_called_once()
    mock_db.save_memory.assert_called_once()
    call_kwargs = mock_db.save_memory.call_args
    assert call_kwargs[1]["summary"] == "Sarah called to wish Rose a happy birthday."
    assert call_kwargs[1]["topics"] == ["birthday", "greeting"]
    assert call_kwargs[1]["mood"] == "happy"
    assert "happy birthday" in call_kwargs[1]["transcript"]


@pytest.mark.asyncio
async def test_call_ended_no_history_skips_save(metadata, mock_db):
    """On CallEnded with no conversation, neither save_memory nor log_call are called."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    mock_db.log_call.assert_not_called()
    mock_db.save_memory.assert_not_called()


@pytest.mark.asyncio
async def test_call_ended_strips_markdown_fences(metadata, mock_db, monkeypatch):
    """LLM responses wrapped in markdown code fences are handled correctly."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    agent._input_history.append(UserTextSent(content="Can you set a reminder for Rose?"))

    fenced_response = '```json\n{"summary": "Sarah requested a reminder for Rose.", "topics": ["reminder"], "mood": "neutral"}\n```'
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=_mock_llm_response(fenced_response)))

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    mock_db.save_memory.assert_called_once()
    assert mock_db.save_memory.call_args[1]["summary"] == "Sarah requested a reminder for Rose."


@pytest.mark.asyncio
async def test_call_ended_handles_missing_fields(metadata, mock_db, monkeypatch):
    """LLM response missing topics/mood uses defaults."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    agent._input_history.append(UserTextSent(content="Hello"))

    partial_response = '{"summary": "Brief greeting call."}'
    monkeypatch.setattr(litellm, "acompletion", AsyncMock(return_value=_mock_llm_response(partial_response)))

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    mock_db.save_memory.assert_called_once()
    call_kwargs = mock_db.save_memory.call_args
    assert call_kwargs[1]["summary"] == "Brief greeting call."
    assert call_kwargs[1]["topics"] == []
    assert call_kwargs[1]["mood"] == "neutral"


@pytest.mark.asyncio
async def test_call_ended_cleans_up_greeter(metadata, mock_db):
    """On CallEnded, greeter.cleanup() is called."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    agent._greeter.cleanup = AsyncMock()

    async for _ in agent.process(MagicMock(), CallEnded()):
        pass

    agent._greeter.cleanup.assert_called_once()
