import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


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
    tool = make_set_reminder(mock_db, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, content="Water the plants", time="3:00 PM")
    mock_db.save_reminder.assert_called_once_with(
        "smith_family", "member_rose", "member_rose", "Water the plants", "3:00 PM", False,
    )


@pytest.mark.asyncio
async def test_set_reminder_returns_confirmation(mock_db):
    from tools.reminder_tools import make_set_reminder
    tool = make_set_reminder(mock_db, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, content="Water plants", time="3:00 PM")
    assert "reminder" in result.lower()


# --- hear_reminders (DeviceUserAgent) ---

@pytest.mark.asyncio
async def test_hear_reminders_returns_formatted(mock_db):
    from tools.reminder_tools import make_hear_reminders
    tool = make_hear_reminders(mock_db, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "Take medicine" in result
    assert "Doctor appointment" in result
    assert "9:00 AM" in result


@pytest.mark.asyncio
async def test_hear_reminders_empty(mock_db_empty):
    from tools.reminder_tools import make_hear_reminders
    tool = make_hear_reminders(mock_db_empty, "smith_family", "member_rose")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx)
    assert "no" in result.lower() and "reminder" in result.lower()


# --- add_reminder (FamilyMemberAgent) ---

@pytest.mark.asyncio
async def test_add_reminder_saves_for_device_user(mock_db):
    from tools.reminder_tools import make_add_reminder
    tool = make_add_reminder(mock_db, "smith_family", "member_sarah")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, content="Take your vitamins", time="8:00 AM")
    call_args = mock_db.save_reminder.call_args
    assert call_args[0][1] == "member_rose"  # for_member_id is device user
    assert call_args[0][2] == "member_sarah"  # created_by is family member


@pytest.mark.asyncio
async def test_add_reminder_returns_confirmation(mock_db):
    from tools.reminder_tools import make_add_reminder
    tool = make_add_reminder(mock_db, "smith_family", "member_sarah")
    mock_ctx = MagicMock()
    result = await tool.func(mock_ctx, content="Take vitamins", time="8:00 AM")
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
    tool_names = agent.tool_names()
    assert not any("add_reminder" in name for name in tool_names)
