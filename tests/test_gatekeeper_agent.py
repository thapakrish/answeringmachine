import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallStarted, CallEnded, UserTextSent, AgentSendText, AgentEndCall


@pytest.fixture
def metadata():
    return {
        "family_id": "smith_family",
        "member_id": None,
        "member_name": "there",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": False,
        "caller_phone": "+19999999999",
        "device_phone": "+15551234567",
    }


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_passphrase = AsyncMock(return_value="sunflower garden")
    db.log_unknown_call = AsyncMock()
    return db


def test_gatekeeper_has_process_method(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    assert hasattr(agent, "process")
    assert callable(agent.process)


@pytest.mark.asyncio
async def test_gatekeeper_greets_with_challenge(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    events = []
    async for event in agent.process(MagicMock(), CallStarted()):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert len(text_events) >= 1
    combined = " ".join(e.text for e in text_events).lower()
    assert "passphrase" in combined


@pytest.mark.asyncio
async def test_correct_passphrase_accepted(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    # Start call first
    async for _ in agent.process(MagicMock(), CallStarted()):
        pass
    # Send correct passphrase
    events = []
    async for event in agent.process(MagicMock(), UserTextSent(content="sunflower garden")):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert any("accepted" in e.text.lower() for e in text_events)


@pytest.mark.asyncio
async def test_wrong_passphrase_gives_retry(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    async for _ in agent.process(MagicMock(), CallStarted()):
        pass
    events = []
    async for event in agent.process(MagicMock(), UserTextSent(content="wrong password")):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert any("not correct" in e.text.lower() or "try again" in e.text.lower() for e in text_events)
    # Should NOT end call on first wrong attempt
    end_events = [e for e in events if isinstance(e, AgentEndCall)]
    assert len(end_events) == 0


@pytest.mark.asyncio
async def test_max_attempts_ends_call(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    async for _ in agent.process(MagicMock(), CallStarted()):
        pass
    # First wrong attempt
    async for _ in agent.process(MagicMock(), UserTextSent(content="wrong1")):
        pass
    # Second wrong attempt - should end call
    events = []
    async for event in agent.process(MagicMock(), UserTextSent(content="wrong2")):
        events.append(event)
    end_events = [e for e in events if isinstance(e, AgentEndCall)]
    assert len(end_events) == 1
    mock_db.log_unknown_call.assert_called_once()


@pytest.mark.asyncio
async def test_no_passphrase_blocks_immediately(metadata, mock_db):
    mock_db.get_passphrase = AsyncMock(return_value=None)
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    events = []
    async for event in agent.process(MagicMock(), CallStarted()):
        events.append(event)
    end_events = [e for e in events if isinstance(e, AgentEndCall)]
    assert len(end_events) == 1


@pytest.mark.asyncio
async def test_call_ended_returns_nothing(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)
    assert len(events) == 0
