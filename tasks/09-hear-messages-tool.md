# Task 09: hear_messages Tool (DeviceUserAgent)

- **Priority**: P0
- **Deps**: Task 07, Task 08
- **PRD**: FR-2.4, FR-5.3

## Objective

Create `hear_messages` loopback tool on DeviceUserAgent that fetches unread messages from Firestore, formats them for spoken delivery, and marks them as read.

## Tests First

```python
# tests/test_hear_messages.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_unread_messages = AsyncMock(return_value=[
        {"id": "msg1", "from_name": "Sarah", "content": "Hi grandma, call me tonight!", "created_at": None},
        {"id": "msg2", "from_name": "Mike", "content": "Happy birthday mom!", "created_at": None},
    ])
    db.mark_messages_read = AsyncMock()
    return db

@pytest.fixture
def mock_db_empty():
    db = AsyncMock()
    db.get_unread_messages = AsyncMock(return_value=[])
    db.mark_messages_read = AsyncMock()
    return db

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


def test_hear_messages_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._greeter._tools]
    assert any("hear_messages" in name for name in tool_names)

@pytest.mark.asyncio
async def test_hear_messages_returns_both_messages(metadata, mock_db):
    from tools.message_tools import make_hear_messages
    hear_messages = make_hear_messages(mock_db, "smith_family", "member_rose")
    result = await hear_messages()
    assert "Sarah" in result
    assert "Mike" in result
    assert "Hi grandma" in result
    assert "Happy birthday" in result

@pytest.mark.asyncio
async def test_hear_messages_marks_as_read(metadata, mock_db):
    from tools.message_tools import make_hear_messages
    hear_messages = make_hear_messages(mock_db, "smith_family", "member_rose")
    await hear_messages()
    mock_db.mark_messages_read.assert_called_once_with("smith_family", ["msg1", "msg2"])

@pytest.mark.asyncio
async def test_hear_messages_no_messages(metadata, mock_db_empty):
    from tools.message_tools import make_hear_messages
    hear_messages = make_hear_messages(mock_db_empty, "smith_family", "member_rose")
    result = await hear_messages()
    assert "no new messages" in result.lower()

@pytest.mark.asyncio
async def test_hear_messages_does_not_mark_when_empty(metadata, mock_db_empty):
    from tools.message_tools import make_hear_messages
    hear_messages = make_hear_messages(mock_db_empty, "smith_family", "member_rose")
    await hear_messages()
    mock_db_empty.mark_messages_read.assert_not_called()
```

## Implementation

```python
# tools/message_tools.py
from line.llm_agent import loopback_tool

def make_hear_messages(db, family_id, member_id):
    @loopback_tool
    async def hear_messages() -> str:
        """Read all unread messages aloud. Call this when the user wants to hear their messages."""
        messages = await db.get_unread_messages(family_id, member_id)
        if not messages:
            return "You have no new messages."

        lines = []
        for msg in messages:
            lines.append(f"Message from {msg['from_name']}: {msg['content']}")

        msg_ids = [msg["id"] for msg in messages]
        await db.mark_messages_read(family_id, msg_ids)

        return "\n".join(lines)

    return hear_messages
```

## Notes

- Tool is created via factory `make_hear_messages(db, family_id, member_id)` to inject dependencies.
- DeviceUserAgent adds it to the greeter's tools list in `__init__`.

## Verification

```bash
pytest tests/test_hear_messages.py -v
```
