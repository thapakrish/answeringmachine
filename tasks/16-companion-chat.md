# Task 16: Companion Chat Handoff

- **Priority**: P1
- **Deps**: Task 07, Task 04
- **PRD**: FR-2.9

## Objective

Add a companion chat LlmAgent to DeviceUserAgent and wire it as a handoff tool using `agent_as_handoff`. The companion is a warm, patient chat partner with memory context.

## Tests First

```python
# tests/test_companion_chat.py
import pytest
from unittest.mock import AsyncMock

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

def test_companion_uses_haiku(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    assert "haiku" in agent._companion._model_id.lower()

def test_companion_handoff_tool_exists(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._greeter._tools]
    assert any("companion" in name.lower() for name in tool_names)

def test_companion_has_end_call(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._companion._tools]
    assert any("end_call" in name for name in tool_names)
```

## Implementation

```python
# agents/device_user_agent.py (additions)
from line.llm_agent import agent_as_handoff
from agents.prompts import COMPANION_PROMPT

# In __init__, add:
self._companion = LlmAgent(
    model="anthropic/claude-haiku-4-5-20251001",
    api_key=self._api_key,
    tools=[end_call],
    config=LlmConfig(
        system_prompt=COMPANION_PROMPT.format(
            member_name=metadata["member_name"],
            member_role=metadata["member_role"],
            preferences=metadata.get("preferences", ""),
            memory_context="",
        ),
    ),
)

# Add companion_chat handoff to greeter's tools:
companion_chat = agent_as_handoff(
    self._companion,
    tool_name="companion_chat",
    tool_description="Transfer to companion chat mode for friendly conversation. Use when the user wants to chat, talk, or have a conversation.",
)
# Add to self._greeter tools list
```

## Notes

- `agent_as_handoff` creates a tool that transfers the call from the greeter to the companion agent.
- The companion can hand back via its own tools or when the conversation naturally ends.
- Companion system prompt should be warm, patient, and reference the user's interests/memory.

## Verification

```bash
pytest tests/test_companion_chat.py -v
```
