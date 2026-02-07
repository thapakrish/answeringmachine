# Task 11: FamilyMemberAgent - Minimal (Greeting + end_call + Guest Restriction)

- **Priority**: P0
- **Deps**: Task 01, Task 04
- **PRD**: FR-3.1, NFR-2

## Objective

Create `FamilyMemberAgent` AgentClass with personalized greeting, `end_call`, and guest tool restriction logic. Tools added in later tasks.

## Tests First

```python
# tests/test_family_member_agent.py
import pytest
from unittest.mock import AsyncMock

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

def test_guest_mode_exact_tools(guest_metadata, mock_db):
    """Guests get ONLY leave_message + end_call. Nothing else."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = set(agent.tool_names())
    # Guests should have exactly these tools
    assert any("leave_message" in name for name in tool_names)
    assert any("end_call" in name for name in tool_names)
    # Guests must NOT have these tools
    assert not any("check_wellness" in name for name in tool_names)
    assert not any("add_reminder" in name for name in tool_names)
    assert not any("leave_anonymous" in name for name in tool_names)

def test_normal_mode_has_leave_message(metadata, mock_db):
    """Normal family members should have leave_message."""
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("leave_message" in name for name in tool_names)
```

## Implementation

```python
# agents/family_member_agent.py
import os
from typing import AsyncIterable
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, CallStarted, CallEnded, InputEvent, OutputEvent
from line.llm_agent import LlmAgent, LlmConfig, end_call
from agents.prompts import FAMILY_MEMBER_GREETER_PROMPT
from tools.message_tools import make_leave_message

class FamilyMemberAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        is_guest = metadata.get("is_guest", False)

        # Build tool list based on guest status
        tools = [
            make_leave_message(db, metadata["family_id"], metadata["member_id"], metadata["member_name"]),
            end_call,
        ]

        # Non-guests get additional tools (added in later tasks)
        if not is_guest:
            pass  # leave_anonymous, check_wellness, add_reminder added in Tasks 12, 19, 18

        device_user_name = "the device user"  # Overwritten below if available

        self._greeter = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=tools,
            config=LlmConfig(
                system_prompt=FAMILY_MEMBER_GREETER_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    device_user_name=device_user_name,
                ),
            ),
        )
        self.model_id = "anthropic/claude-haiku-4-5-20251001"

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            name = self._metadata["member_name"]
            yield AgentSendText(text=f"Hi {name}! How can I help you today?")
            return

        if isinstance(event, CallEnded):
            await self._greeter.cleanup()
            return

        async for output in self._greeter.process(env, event):
            yield output
```

## Notes

- Guest tool restriction is enforced at tool-list level: the LLM literally cannot call tools it doesn't have.
- Additional tools (leave_anonymous, check_wellness, add_reminder) are added in Tasks 12, 18, 19 by modifying the `if not is_guest` block.

## Verification

```bash
pytest tests/test_family_member_agent.py -v
```
