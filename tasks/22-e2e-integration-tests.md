# Task 22: End-to-End Integration Tests

- **Priority**: P0
- **Deps**: All previous tasks
- **PRD**: Success Criteria

## Objective

Integration tests that verify complete call flows end-to-end, using mocked DB but real agent logic.

## Tests

```python
# tests/test_e2e.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallStarted, CallEnded, UserTextSent, AgentSendText, AgentEndCall

# --- Fixtures ---

@pytest.fixture
def device_user_metadata():
    return {
        "family_id": "smith_family",
        "member_id": "member_rose",
        "member_name": "Rose",
        "member_role": "grandparent",
        "is_device_user": True,
        "is_authorized": True,
    }

@pytest.fixture
def family_member_metadata():
    return {
        "family_id": "smith_family",
        "member_id": "member_sarah",
        "member_name": "Sarah",
        "member_role": "granddaughter",
        "is_device_user": False,
        "is_authorized": True,
    }

@pytest.fixture
def unknown_caller_metadata():
    return {
        "family_id": "smith_family",
        "member_id": None,
        "member_name": "there",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": False,
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
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [
            {"date": "2025-01-15", "summary": "Talked about mystery novels", "topics": ["reading"], "mood": "happy"},
        ],
        "preferences": {"interests": ["mystery novels", "gardening"]},
        "last_interaction": "2025-01-15T10:30:00",
    })
    db.get_unread_messages = AsyncMock(return_value=[
        {"id": "msg1", "from_name": "Sarah", "content": "Hi grandma, call me tonight!"},
    ])
    db.mark_messages_read = AsyncMock()
    db.save_message = AsyncMock(return_value="msg_new")
    db.save_memory = AsyncMock()
    db.get_reminders = AsyncMock(return_value=[])
    db.save_reminder = AsyncMock(return_value="rem_1")
    db.get_passphrase = AsyncMock(return_value="sunflower garden")
    db.log_unknown_call = AsyncMock()
    db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    db.get_recent_call_logs = AsyncMock(return_value=[])
    return db

@pytest.fixture
def mock_env():
    return MagicMock()


# --- Device User Flows ---

@pytest.mark.asyncio
async def test_device_user_greeting_flow(device_user_metadata, mock_db, mock_env):
    """Device user picks up → personalized greeting with unread count."""
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=device_user_metadata, db=mock_db)

    events = []
    async for event in agent.process(mock_env, CallStarted()):
        events.append(event)

    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert len(text_events) >= 1
    greeting = text_events[0].text.lower()
    assert "rose" in greeting

@pytest.mark.asyncio
async def test_device_user_call_ended_saves_memory(device_user_metadata, mock_db, mock_env):
    """On CallEnded, memory is saved if there was a conversation."""
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=device_user_metadata, db=mock_db)
    agent._conversation_summary = "Discussed the weather"
    agent._conversation_topics = ["weather"]
    agent._conversation_mood = "neutral"

    async for _ in agent.process(mock_env, CallEnded()):
        pass

    mock_db.save_memory.assert_called_once()


# --- Family Member Flows ---

@pytest.mark.asyncio
async def test_family_member_greeting(family_member_metadata, mock_db, mock_env):
    """Family member calls → greeted by name."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=family_member_metadata, db=mock_db)

    events = []
    async for event in agent.process(mock_env, CallStarted()):
        events.append(event)

    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert len(text_events) >= 1
    assert "sarah" in text_events[0].text.lower()


# --- Gatekeeper Flows ---

@pytest.mark.asyncio
async def test_unknown_caller_passphrase_correct(unknown_caller_metadata, mock_db, mock_env):
    """Unknown caller → passphrase challenge → correct → accepted."""
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=unknown_caller_metadata, db=mock_db)

    # CallStarted → challenge
    events = []
    async for event in agent.process(mock_env, CallStarted()):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert any("passphrase" in e.text.lower() for e in text_events)

    # Correct passphrase
    events = []
    async for event in agent.process(mock_env, UserTextSent(text="sunflower garden")):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert any("accepted" in e.text.lower() for e in text_events)

@pytest.mark.asyncio
async def test_unknown_caller_passphrase_wrong(unknown_caller_metadata, mock_db, mock_env):
    """Unknown caller → passphrase challenge → wrong twice → logged + ended."""
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=unknown_caller_metadata, db=mock_db)

    async for _ in agent.process(mock_env, CallStarted()):
        pass

    # First wrong attempt
    events = []
    async for event in agent.process(mock_env, UserTextSent(text="wrong answer")):
        events.append(event)
    assert not any(isinstance(e, AgentEndCall) for e in events)

    # Second wrong attempt → end call
    events = []
    async for event in agent.process(mock_env, UserTextSent(text="still wrong")):
        events.append(event)
    assert any(isinstance(e, AgentEndCall) for e in events)
    mock_db.log_unknown_call.assert_called_once()


# --- Guest Restrictions ---

def test_guest_cannot_check_wellness(guest_metadata, mock_db):
    """Guest session must NOT have check_wellness tool."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert not any("check_wellness" in name for name in tool_names)

def test_guest_cannot_add_reminder(guest_metadata, mock_db):
    """Guest session must NOT have add_reminder tool."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert not any("add_reminder" in name for name in tool_names)

def test_guest_cannot_leave_anonymous(guest_metadata, mock_db):
    """Guest session must NOT have leave_anonymous tool."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert not any("leave_anonymous" in name for name in tool_names)

def test_guest_has_only_leave_message_and_end_call(guest_metadata, mock_db):
    """Guest should have exactly leave_message + end_call."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("leave_message" in name for name in tool_names)
    assert any("end_call" in name for name in tool_names)
    # Total tools should be exactly 2
    assert len(agent._greeter._tools) == 2


# --- Anonymous Message ---

@pytest.mark.asyncio
async def test_anonymous_message_attribution(mock_db):
    """Anonymous messages should be attributed to 'A family member'."""
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    await leave_anonymous(message_content="Surprise!")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["from_name"] == "A family member"
    assert call_args.kwargs["from_member_id"] == "anonymous"
```

## Notes

- These tests use mocked DB but real agent logic to verify complete flows.
- Some tests (like the LLM tool-calling ones) would need a real API key for full integration testing. The tests here focus on the deterministic routing and state management.
- Run against a real Firestore (or emulator) for deeper integration testing.

## Verification

```bash
pytest tests/test_e2e.py -v
```
