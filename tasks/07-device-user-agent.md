# Task 07: DeviceUserAgent - Minimal (Greeting + end_call)

- **Priority**: P0
- **Deps**: Task 01, Task 04
- **PRD**: FR-2.1, NFR-2

## Objective

Create `DeviceUserAgent` AgentClass with personalized greeting and `end_call`. Minimal viable agent — tools added in later tasks.

## Tests First

```python
# tests/test_device_user_agent.py
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
    db.get_memory = AsyncMock(return_value={"recent_conversations": [], "preferences": {}})
    db.get_unread_messages = AsyncMock(return_value=[])
    return db


def test_agent_has_process_method(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    assert hasattr(agent, "process")
    assert callable(agent.process)

def test_agent_uses_haiku(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    assert "haiku" in agent.model_id.lower()

def test_agent_has_end_call_tool(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("end_call" in name for name in tool_names)
```

## Implementation

```python
# agents/device_user_agent.py
import os
from typing import AsyncIterable
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, CallStarted, CallEnded, InputEvent, OutputEvent
from line.llm_agent import LlmAgent, LlmConfig, end_call
from agents.prompts import DEVICE_USER_GREETER_PROMPT

class DeviceUserAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")

        self._greeter = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=[end_call],
            config=LlmConfig(
                system_prompt=DEVICE_USER_GREETER_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    preferences="",
                    memory_context="",
                ),
            ),
        )
        self.model_id = "anthropic/claude-haiku-4-5-20251001"

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            name = self._metadata["member_name"]
            yield AgentSendText(text=f"Hello, {name}! What would you like to do?")
            return

        if isinstance(event, CallEnded):
            await self._greeter.cleanup()
            return

        async for output in self._greeter.process(env, event):
            yield output
```

## Notes

- Greeting is minimal here. Task 10 (dynamic greeting) adds memory + unread count.
- Tools added incrementally in Tasks 08, 09, 11, 12, 13.

## Verification

```bash
pytest tests/test_device_user_agent.py -v
```
