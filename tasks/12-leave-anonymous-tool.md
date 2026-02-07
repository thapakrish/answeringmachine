# Task 12: leave_anonymous Tool (FamilyMemberAgent)

- **Priority**: P1
- **Deps**: Task 08, Task 11
- **PRD**: FR-3.3

## Objective

Create `leave_anonymous` loopback tool that lets recognized family members leave a message attributed to "A family member" instead of their real name.

## Tests First

```python
# tests/test_leave_anonymous.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_message = AsyncMock(return_value="msg_anon_1")
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


@pytest.mark.asyncio
async def test_leave_anonymous_from_name(mock_db):
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    await leave_anonymous(message_content="Happy birthday surprise coming!")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["from_name"] == "A family member"

@pytest.mark.asyncio
async def test_leave_anonymous_from_id(mock_db):
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    await leave_anonymous(message_content="Check the garden")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["from_member_id"] == "anonymous"

@pytest.mark.asyncio
async def test_leave_anonymous_content_saved(mock_db):
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    await leave_anonymous(message_content="There's a surprise in the mail")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["content"] == "There's a surprise in the mail"

@pytest.mark.asyncio
async def test_leave_anonymous_targets_device_user(mock_db):
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    await leave_anonymous(message_content="Secret message")
    call_args = mock_db.save_message.call_args
    assert call_args.kwargs["to_member_id"] == "member_rose"

@pytest.mark.asyncio
async def test_leave_anonymous_returns_confirmation(mock_db):
    from tools.message_tools import make_leave_anonymous
    leave_anonymous = make_leave_anonymous(mock_db, "smith_family")
    result = await leave_anonymous(message_content="Surprise!")
    assert "anonymous" in result.lower() or "family member" in result.lower()

def test_guest_does_not_have_leave_anonymous():
    """Guests must NOT have the leave_anonymous tool."""
    from unittest.mock import AsyncMock
    from agents.family_member_agent import FamilyMemberAgent
    mock_db = AsyncMock()
    mock_db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    guest_metadata = {
        "family_id": "smith_family",
        "member_id": "guest",
        "member_name": "Guest",
        "member_role": "unknown",
        "is_device_user": False,
        "is_authorized": True,
        "is_guest": True,
    }
    agent = FamilyMemberAgent(metadata=guest_metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert not any("leave_anonymous" in name for name in tool_names)
```

## Implementation

```python
# tools/message_tools.py (additions)

def make_leave_anonymous(db, family_id):
    @loopback_tool
    async def leave_anonymous(message_content: str) -> str:
        """Leave an anonymous message for the device user. The recipient will see it as 'A family member' instead of your name. Use when the caller wants to leave a surprise or private message."""
        device_user = await db.get_primary_device_user(family_id)
        to_member_id = device_user["id"] if device_user else "unknown"

        await db.save_message(
            family_id=family_id,
            from_member_id="anonymous",
            from_name="A family member",
            to_member_id=to_member_id,
            content=message_content,
        )
        return "Your anonymous message has been saved. It will appear as 'A family member'."

    return leave_anonymous
```

## Notes

- Only available to recognized family members (NOT guests). Enforced in FamilyMemberAgent's tool list.
- Wire into FamilyMemberAgent `__init__` in the `if not is_guest` block.

## Verification

```bash
pytest tests/test_leave_anonymous.py -v
```
