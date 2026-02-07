# Task 21: GatekeeperAgent + Passphrase/Logging Operations

- **Priority**: P1
- **Deps**: Task 02, Task 04, Task 06, Task 11
- **PRD**: FR-1.5, FR-1.6, FR-1.7, FR-4.1, FR-4.2, FR-4.3

## Objective

Create `GatekeeperAgent` that challenges unknown callers with a family passphrase. Correct passphrase grants a one-off guest session (FamilyMemberAgent with restricted tools). Wrong passphrase logs the attempt and ends the call.

Also add `get_passphrase` and `log_unknown_call` to FirebaseClient.

## Tests First

```python
# tests/test_gatekeeper_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from line.events import CallStarted, CallEnded

@pytest.fixture
def metadata():
    return {
        "family_id": "smith_family",
        "member_id": None,
        "member_name": "there",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": False,
    }

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_passphrase = AsyncMock(return_value="sunflower garden")
    db.log_unknown_call = AsyncMock()
    db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    return db


def test_gatekeeper_has_process_method(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    assert hasattr(agent, "process")
    assert callable(agent.process)

@pytest.mark.asyncio
async def test_gatekeeper_greets_with_challenge(metadata, mock_db):
    from agents.gatekeeper_agent import GatekeeperAgent
    from line.events import AgentSendText
    agent = GatekeeperAgent(metadata=metadata, db=mock_db)
    events = []
    async for event in agent.process(MagicMock(), CallStarted()):
        events.append(event)
    text_events = [e for e in events if isinstance(e, AgentSendText)]
    assert len(text_events) >= 1
    combined = " ".join(e.text for e in text_events).lower()
    assert "passphrase" in combined or "password" in combined or "identify" in combined


# --- FirebaseClient passphrase/logging ---

@pytest.fixture
def mock_db_for_firebase():
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_passphrase(mock_db):
    result = await mock_db.get_passphrase("smith_family")
    assert result == "sunflower garden"

@pytest.mark.asyncio
async def test_get_passphrase_none():
    db = AsyncMock()
    db.get_passphrase = AsyncMock(return_value=None)
    result = await db.get_passphrase("no_passphrase_family")
    assert result is None

@pytest.mark.asyncio
async def test_log_unknown_call(mock_db):
    await mock_db.log_unknown_call("+19999999999", "+15551234567", "smith_family")
    mock_db.log_unknown_call.assert_called_once()

@pytest.mark.asyncio
async def test_log_call():
    db = AsyncMock()
    db.log_call = AsyncMock()
    await db.log_call("smith_family", "+15559876543", "member_sarah", "Sarah", "Left a message", False)
    db.log_call.assert_called_once()
```

## Implementation

```python
# agents/gatekeeper_agent.py
import os
from typing import AsyncIterable
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, AgentEndCall, CallStarted, CallEnded, UserTextSent, InputEvent, OutputEvent
from agents.prompts import GATEKEEPER_PROMPT

class GatekeeperAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._passphrase = None
        self._attempts = 0
        self._max_attempts = 2

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            self._passphrase = await self._db.get_passphrase(self._metadata["family_id"])
            if not self._passphrase:
                yield AgentSendText(text="This number is not accepting calls from unregistered numbers. Goodbye.")
                yield AgentEndCall()
                return
            yield AgentSendText(text="Hello! This number uses a family passphrase for unregistered callers. Please say the family passphrase to continue.")
            return

        if isinstance(event, CallEnded):
            return

        if isinstance(event, UserTextSent):
            user_input = event.text.strip().lower()
            if self._passphrase and user_input == self._passphrase.lower():
                yield AgentSendText(text="Passphrase accepted! Connecting you now.")
                # Handoff to guest family member agent (implementation depends on Line SDK):
                # Option A: yield agent_as_handoff(FamilyMemberAgent(...))
                # Option B: return a new agent instance if supported by app
                return

            self._attempts += 1
            if self._attempts >= self._max_attempts:
                await self._db.log_unknown_call(
                    phone=self._metadata.get("caller_phone", "unknown"),
                    device_phone=self._metadata.get("device_phone", "unknown"),
                    family_id=self._metadata["family_id"],
                )
                yield AgentSendText(text="Incorrect passphrase. This call has been logged. Goodbye.")
                yield AgentEndCall()
                return

            remaining = self._max_attempts - self._attempts
            yield AgentSendText(text=f"That's not correct. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining. Please try again.")


# firebase_client.py (additions)

async def get_passphrase(self, family_id):
    doc = await self.db.collection("families").document(family_id).get()
    if not doc.exists:
        return None
    return doc.to_dict().get("passphrase")

async def log_unknown_call(self, phone, device_phone, family_id):
    ref = self.db.collection("unknown_call_attempts").document()
    await ref.set({
        "phone_number": phone,
        "target_device_phone": device_phone,
        "family_id": family_id,
        "timestamp": SERVER_TIMESTAMP,
        "blocked": True,
    })

async def log_call(self, family_id, caller_phone, member_id, member_name, summary, is_anonymous):
    ref = self.db.collection("families").document(family_id).collection("call_logs").document()
    await ref.set({
        "caller_phone": caller_phone,
        "caller_member_id": member_id,
        "caller_name": member_name,
        "timestamp": SERVER_TIMESTAMP,
        "summary": summary,
        "is_anonymous": is_anonymous,
    })
```

## Notes

- GatekeeperAgent does NOT use an LlmAgent — it's a simple state machine (deterministic).
- Max 2 passphrase attempts before logging and ending the call.
- On correct passphrase, the current implementation sends an acceptance message. Full guest session handoff requires `agent_as_handoff` or returning a new agent — this may need integration with the agent factory.
- `get_passphrase` reads the `passphrase` field from the family document (not a subcollection).

## Verification

```bash
pytest tests/test_gatekeeper_agent.py -v
```
