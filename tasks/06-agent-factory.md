# Task 06: get_agent - Agent Factory & main.py Wiring

- **Priority**: P0
- **Deps**: Task 05, Task 07, Task 08
- **PRD**: FR-1.3, FR-1.4, FR-1.5

## Objective

Implement `get_agent` in `main.py` to route calls to the correct agent based on metadata. Wire up `VoiceAgentApp`.

## Tests First

```python
# tests/test_get_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def make_call_request():
    def _make(metadata):
        req = MagicMock()
        req.metadata = metadata
        return req
    return _make

@pytest.mark.asyncio
async def test_device_user_gets_device_user_agent(mock_db, make_call_request):
    from main import make_get_agent
    from agents.device_user_agent import DeviceUserAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": True, "is_authorized": True, "family_id": "f1", "member_id": "m1", "member_name": "Rose", "member_role": "grandparent"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, DeviceUserAgent)

@pytest.mark.asyncio
async def test_family_member_gets_family_member_agent(mock_db, make_call_request):
    from main import make_get_agent
    from agents.family_member_agent import FamilyMemberAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": False, "is_authorized": True, "family_id": "f1", "member_id": "m2", "member_name": "Sarah", "member_role": "granddaughter"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, FamilyMemberAgent)

@pytest.mark.asyncio
async def test_unauthorized_gets_gatekeeper(mock_db, make_call_request):
    from main import make_get_agent
    from agents.gatekeeper_agent import GatekeeperAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": False, "is_authorized": False, "family_id": "f1", "member_id": None, "member_name": "there", "member_role": "unknown"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, GatekeeperAgent)
```

## Implementation

```python
# main.py (complete wiring)

from firebase_client import FirebaseClient
from agents.device_user_agent import DeviceUserAgent
from agents.family_member_agent import FamilyMemberAgent
from agents.gatekeeper_agent import GatekeeperAgent
from line.voice_agent_app import VoiceAgentApp

db = FirebaseClient()

def make_get_agent(db):
    async def get_agent(env, call_request):
        metadata = call_request.metadata or {}
        if not metadata.get("is_authorized", True):
            return GatekeeperAgent(metadata=metadata, db=db)
        if metadata.get("is_device_user", False):
            return DeviceUserAgent(metadata=metadata, db=db)
        return FamilyMemberAgent(metadata=metadata, db=db)
    return get_agent

app = VoiceAgentApp(
    get_agent=make_get_agent(db),
    pre_call_handler=make_pre_call_handler(db),
)

if __name__ == "__main__":
    print("AnsweringMachine is running")
    app.run()
```

## Verification

```bash
pytest tests/test_get_agent.py -v
ANTHROPIC_API_KEY=... PORT=8000 uv run python main.py  # Starts without error
```
