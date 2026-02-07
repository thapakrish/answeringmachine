# Task 14: Dynamic Greeting with Memory + Unread Count

- **Priority**: P1
- **Deps**: Task 07, Task 08, Task 13
- **PRD**: FR-2.1, FR-2.2, FR-2.3

## Objective

Enhance DeviceUserAgent's `CallStarted` handler to build a dynamic greeting that includes time-of-day greeting, unread message count, and memory callbacks from past conversations.

## Tests First

```python
# tests/test_dynamic_greeting.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

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
def mock_db_with_data():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [
            {"date": "2025-01-01", "summary": "Rose talked about finishing a mystery novel", "topics": ["mystery novels"], "mood": "happy"},
        ],
        "preferences": {"interests": ["mystery novels", "gardening"]},
        "last_interaction": "2025-01-01",
    })
    db.get_unread_messages = AsyncMock(return_value=[
        {"id": "msg1", "from_name": "Sarah", "content": "Hi grandma"},
        {"id": "msg2", "from_name": "Mike", "content": "Hello mom"},
        {"id": "msg3", "from_name": "Emma", "content": "Hi great-grandma"},
    ])
    return db

@pytest.fixture
def mock_db_empty():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={"recent_conversations": [], "preferences": {}})
    db.get_unread_messages = AsyncMock(return_value=[])
    return db


@pytest.mark.asyncio
async def test_greeting_includes_morning(metadata, mock_db_with_data):
    from agents.device_user_agent import DeviceUserAgent, _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "good morning" in greeting.lower()

@pytest.mark.asyncio
async def test_greeting_includes_evening(metadata, mock_db_with_data):
    from agents.device_user_agent import DeviceUserAgent, _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 19, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "good evening" in greeting.lower()

@pytest.mark.asyncio
async def test_greeting_includes_unread_count(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "3" in greeting
    assert "message" in greeting.lower()

@pytest.mark.asyncio
async def test_greeting_includes_memory(metadata, mock_db_with_data):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_with_data)
    assert "mystery novel" in greeting.lower()

@pytest.mark.asyncio
async def test_greeting_no_memory_still_works(metadata, mock_db_empty):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_empty)
    assert metadata["member_name"] in greeting
    # Should not crash or mention memory

@pytest.mark.asyncio
async def test_greeting_no_messages_no_mention(metadata, mock_db_empty):
    from agents.device_user_agent import _build_greeting
    with patch("agents.device_user_agent.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2025, 6, 15, 9, 0, 0)
        greeting = await _build_greeting(metadata, mock_db_empty)
    # Should not say "0 messages" — just omit message count
    assert "0 " not in greeting
```

## Implementation

```python
# agents/device_user_agent.py (modification)
from datetime import datetime

async def _build_greeting(metadata, db):
    name = metadata["member_name"]
    family_id = metadata["family_id"]
    member_id = metadata["member_id"]

    # Time of day
    hour = datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 17:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"

    parts = [f"{time_greeting}, {name}!"]

    # Unread messages
    unread = await db.get_unread_messages(family_id, member_id)
    if unread:
        count = len(unread)
        parts.append(f"You have {count} new message{'s' if count != 1 else ''}.")

    # Memory callback
    memory = await db.get_memory(family_id, member_id)
    convos = memory.get("recent_conversations", [])
    if convos:
        last = convos[-1]
        parts.append(f"Last time we talked, you mentioned {last['summary'].lower()}.")

    parts.append("What would you like to do?")
    return " ".join(parts)
```

## Notes

- `_build_greeting` is a module-level async function (not a method) for easier testing.
- Called from `DeviceUserAgent.process()` when handling `CallStarted`.

## Verification

```bash
pytest tests/test_dynamic_greeting.py -v
```
