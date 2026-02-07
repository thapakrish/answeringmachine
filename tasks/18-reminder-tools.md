# Task 18: Reminder Tools (set_reminder, hear_reminders, add_reminder)

- **Priority**: P1
- **Deps**: Task 17, Task 07, Task 11
- **PRD**: FR-2.5, FR-2.6, FR-3.5

## Objective

Create three reminder tools:
- `set_reminder` — DeviceUserAgent sets their own reminder
- `hear_reminders` — DeviceUserAgent hears active reminders
- `add_reminder` — FamilyMemberAgent sets a reminder for the device user

## Tests First

```python
# tests/test_reminder_tools.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.save_reminder = AsyncMock(return_value="rem_123")
    db.get_reminders = AsyncMock(return_value=[
        {"id": "rem1", "content": "Take medicine", "time": "9:00 AM", "recurring": True, "created_by_member_id": "member_sarah"},
        {"id": "rem2", "content": "Doctor appointment", "time": "2:00 PM Friday", "recurring": False, "created_by_member_id": "member_rose"},
    ])
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db

@pytest.fixture
def mock_db_empty():
    db = AsyncMock()
    db.get_reminders = AsyncMock(return_value=[])
    return db


# --- set_reminder (DeviceUserAgent) ---

@pytest.mark.asyncio
async def test_set_reminder_saves(mock_db):
    from tools.reminder_tools import make_set_reminder
    set_reminder = make_set_reminder(mock_db, "smith_family", "member_rose")
    result = await set_reminder(content="Water the plants", time="3:00 PM")
    mock_db.save_reminder.assert_called_once_with(
        "smith_family", "member_rose", "member_rose", "Water the plants", "3:00 PM", False,
    )

@pytest.mark.asyncio
async def test_set_reminder_returns_confirmation(mock_db):
    from tools.reminder_tools import make_set_reminder
    set_reminder = make_set_reminder(mock_db, "smith_family", "member_rose")
    result = await set_reminder(content="Water plants", time="3:00 PM")
    assert "reminder" in result.lower()

# --- hear_reminders (DeviceUserAgent) ---

@pytest.mark.asyncio
async def test_hear_reminders_returns_formatted(mock_db):
    from tools.reminder_tools import make_hear_reminders
    hear_reminders = make_hear_reminders(mock_db, "smith_family", "member_rose")
    result = await hear_reminders()
    assert "Take medicine" in result
    assert "Doctor appointment" in result
    assert "9:00 AM" in result

@pytest.mark.asyncio
async def test_hear_reminders_empty(mock_db_empty):
    from tools.reminder_tools import make_hear_reminders
    hear_reminders = make_hear_reminders(mock_db_empty, "smith_family", "member_rose")
    result = await hear_reminders()
    assert "no" in result.lower() and "reminder" in result.lower()

# --- add_reminder (FamilyMemberAgent) ---

@pytest.mark.asyncio
async def test_add_reminder_saves_for_device_user(mock_db):
    from tools.reminder_tools import make_add_reminder
    add_reminder = make_add_reminder(mock_db, "smith_family", "member_sarah")
    result = await add_reminder(content="Take your vitamins", time="8:00 AM")
    call_args = mock_db.save_reminder.call_args
    assert call_args[0][1] == "member_rose"  # for_member_id is device user
    assert call_args[0][2] == "member_sarah"  # created_by is family member

@pytest.mark.asyncio
async def test_add_reminder_returns_confirmation(mock_db):
    from tools.reminder_tools import make_add_reminder
    add_reminder = make_add_reminder(mock_db, "smith_family", "member_sarah")
    result = await add_reminder(content="Take vitamins", time="8:00 AM")
    assert "reminder" in result.lower()

# --- Guest restriction ---

def test_guest_does_not_have_add_reminder():
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
    tool_names = [t.__name__ if callable(t) else str(t) for t in agent._greeter._tools]
    assert not any("add_reminder" in name for name in tool_names)
```

## Implementation

```python
# tools/reminder_tools.py
from line.llm_agent import loopback_tool

def make_set_reminder(db, family_id, member_id):
    @loopback_tool
    async def set_reminder(content: str, time: str) -> str:
        """Set a reminder for yourself. Provide what to remember and when."""
        await db.save_reminder(family_id, member_id, member_id, content, time, False)
        return f"Reminder set: '{content}' at {time}."
    return set_reminder

def make_hear_reminders(db, family_id, member_id):
    @loopback_tool
    async def hear_reminders() -> str:
        """Read all active reminders aloud."""
        reminders = await db.get_reminders(family_id, member_id)
        if not reminders:
            return "You have no active reminders."
        lines = []
        for rem in reminders:
            lines.append(f"Reminder: {rem['content']} at {rem['time']}")
        return "\n".join(lines)
    return hear_reminders

def make_add_reminder(db, family_id, from_member_id):
    @loopback_tool
    async def add_reminder(content: str, time: str) -> str:
        """Add a reminder for the device user. Provide what to remind about and when."""
        device_user = await db.get_primary_device_user(family_id)
        for_member_id = device_user["id"] if device_user else "unknown"
        await db.save_reminder(family_id, for_member_id, from_member_id, content, time, False)
        return f"Reminder added for {device_user['name']}: '{content}' at {time}."
    return add_reminder
```

## Verification

```bash
pytest tests/test_reminder_tools.py -v
```
