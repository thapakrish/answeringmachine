# Task 10: leave_message Tool (FamilyMemberAgent)

- **Priority**: P0
- **Deps**: Task 08
- **PRD**: FR-3.2, FR-3.6, FR-5.3

## Objective

Create `leave_message` loopback tool for FamilyMemberAgent that saves a voice message to Firestore for the device user.

## Tests First

```python
# tests/test_leave_message.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_message = AsyncMock(return_value="msg_123")
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db

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


def test_leave_message_tool_on_agent(metadata, mock_db):
    from agents.family_member_agent import FamilyMemberAgent
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._greeter._tools]
    assert any("leave_message" in name for name in tool_names)

@pytest.mark.asyncio
async def test_leave_message_saves_to_firestore(mock_db):
    from tools.message_tools import make_leave_message
    leave_message = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    result = await leave_message(message_content="Tell grandma I'll visit Sunday")
    mock_db.save_message.assert_called_once()
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["content"] == "Tell grandma I'll visit Sunday"
    assert call_args.kwargs["from_member_id"] == "member_sarah"
    assert call_args.kwargs["from_name"] == "Sarah"

@pytest.mark.asyncio
async def test_leave_message_targets_device_user(mock_db):
    from tools.message_tools import make_leave_message
    leave_message = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    await leave_message(message_content="Hello grandma")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["to_member_id"] == "member_rose"

@pytest.mark.asyncio
async def test_leave_message_returns_confirmation(mock_db):
    from tools.message_tools import make_leave_message
    leave_message = make_leave_message(mock_db, "smith_family", "member_sarah", "Sarah")
    result = await leave_message(message_content="See you Sunday")
    assert "message" in result.lower()
    assert "delivered" in result.lower() or "saved" in result.lower() or "left" in result.lower()
```

## Implementation

```python
# tools/message_tools.py (additions)

def make_leave_message(db, family_id, from_member_id, from_name):
    @loopback_tool
    async def leave_message(message_content: str) -> str:
        """Leave a message for the device user. Call this when the caller wants to leave a message."""
        device_user = await db.get_primary_device_user(family_id)
        to_member_id = device_user["id"] if device_user else "unknown"

        await db.save_message(
            family_id=family_id,
            from_member_id=from_member_id,
            from_name=from_name,
            to_member_id=to_member_id,
            content=message_content,
        )
        return "Your message has been saved and will be delivered."

    return leave_message
```

## Verification

```bash
pytest tests/test_leave_message.py -v
```
