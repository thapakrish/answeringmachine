# Task 15: Save Memory on CallEnded

- **Priority**: P1
- **Deps**: Task 07, Task 13
- **PRD**: FR-2.10

## Objective

When a DeviceUserAgent call ends, summarize the conversation and save it to the memory collection in Firestore.

## Tests First

```python
# tests/test_save_memory_call_ended.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallEnded

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
    # Simulate some conversation history
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

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    agent._greeter.cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_call_ended_no_summary_skips_save(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    # No conversation summary set — short call

    events = []
    async for event in agent.process(MagicMock(), CallEnded()):
        events.append(event)

    mock_db.save_memory.assert_not_called()
```

## Implementation

```python
# agents/device_user_agent.py (modification to CallEnded handler)

# In __init__, add:
self._conversation_summary = None
self._conversation_topics = []
self._conversation_mood = "neutral"

# In process(), modify CallEnded handling:
if isinstance(event, CallEnded):
    if self._conversation_summary:
        await self._db.save_memory(
            self._metadata["family_id"],
            self._metadata["member_id"],
            summary=self._conversation_summary,
            topics=self._conversation_topics,
            mood=self._conversation_mood,
        )
    await self._greeter.cleanup()
    return
```

## Notes

- Conversation summary is built up during the call. A simple approach: track key topics mentioned during tool calls.
- A more advanced approach (stretch): use a final LLM call to summarize before saving. This can be added later.
- The `_conversation_summary`, `_conversation_topics`, and `_conversation_mood` attributes are set by tool handlers during the call.

## Verification

```bash
pytest tests/test_save_memory_call_ended.py -v
```
