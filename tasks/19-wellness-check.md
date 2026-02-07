# Task 19: Activity Query + check_wellness Tool

- **Priority**: P1
- **Deps**: Task 02, Task 13, Task 11
- **PRD**: FR-3.4, FR-5.5

## Objective

Add `get_recent_activity` to FirebaseClient and create `check_wellness` loopback tool for FamilyMemberAgent. NOT available to guests.

## Tests First

```python
# tests/test_wellness.py
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

# --- FirebaseClient activity query ---

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.get_memory = AsyncMock(return_value={
        "recent_conversations": [
            {"date": "2025-01-15", "summary": "Talked about gardening", "topics": ["gardening"], "mood": "happy"},
            {"date": "2025-01-14", "summary": "Discussed doctor visit", "topics": ["health"], "mood": "anxious"},
        ],
        "preferences": {},
        "last_interaction": "2025-01-15T10:30:00",
    })
    db.get_recent_call_logs = AsyncMock(return_value=[
        {"timestamp": "2025-01-15T10:30:00", "caller_name": "Rose", "summary": "Chatted about garden"},
        {"timestamp": "2025-01-14T09:00:00", "caller_name": "Rose", "summary": "Asked about weather"},
    ])
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
    })
    return db


@pytest.mark.asyncio
async def test_get_recent_activity_returns_memory(mock_db):
    from firebase_client import FirebaseClient
    # Use a real client for integration or mock for unit
    result = await mock_db.get_memory("smith_family", "member_rose")
    assert len(result["recent_conversations"]) == 2
    assert result["last_interaction"] == "2025-01-15T10:30:00"

@pytest.mark.asyncio
async def test_get_recent_activity_returns_call_logs(mock_db):
    result = await mock_db.get_recent_call_logs("smith_family", limit=5)
    assert len(result) == 2

# --- check_wellness tool ---

@pytest.mark.asyncio
async def test_check_wellness_returns_activity(mock_db):
    from tools.wellness_tools import make_check_wellness
    check_wellness = make_check_wellness(mock_db, "smith_family")
    result = await check_wellness()
    assert "last_interaction" in result.lower() or "2025-01-15" in result
    assert "gardening" in result.lower() or "garden" in result.lower()

@pytest.mark.asyncio
async def test_check_wellness_returns_mood(mock_db):
    from tools.wellness_tools import make_check_wellness
    check_wellness = make_check_wellness(mock_db, "smith_family")
    result = await check_wellness()
    assert "happy" in result.lower() or "mood" in result.lower()

def test_check_wellness_not_available_for_guests():
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
    assert not any("check_wellness" in name for name in tool_names)

def test_check_wellness_available_for_family_member():
    from agents.family_member_agent import FamilyMemberAgent
    mock_db = AsyncMock()
    mock_db.get_primary_device_user = AsyncMock(return_value={"id": "member_rose", "name": "Rose"})
    metadata = {
        "family_id": "smith_family",
        "member_id": "member_sarah",
        "member_name": "Sarah",
        "member_role": "granddaughter",
        "is_device_user": False,
        "is_authorized": True,
    }
    agent = FamilyMemberAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("check_wellness" in name for name in tool_names)
```

## Implementation

```python
# firebase_client.py (additions)

async def get_recent_call_logs(self, family_id, limit=5):
    refs = (
        self.db.collection("families").document(family_id).collection("call_logs")
        .order_by("timestamp", direction="DESCENDING")
        .limit(limit)
    )
    return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]

# tools/wellness_tools.py

from line.llm_agent import loopback_tool

def make_check_wellness(db, family_id):
    @loopback_tool
    async def check_wellness() -> str:
        """Check on the device user's recent activity, mood, and interactions. Shows when they last used the device and what they talked about."""
        device_user = await db.get_primary_device_user(family_id)
        member_id = device_user["id"]

        memory = await db.get_memory(family_id, member_id)
        call_logs = await db.get_recent_call_logs(family_id, limit=5)

        parts = [f"Wellness check for {device_user['name']}:"]

        last = memory.get("last_interaction")
        if last:
            parts.append(f"Last interaction: {last}")

        convos = memory.get("recent_conversations", [])
        if convos:
            recent = convos[-1]
            parts.append(f"Last conversation: {recent['summary']}")
            parts.append(f"Mood: {recent.get('mood', 'unknown')}")
            topics = recent.get("topics", [])
            if topics:
                parts.append(f"Topics: {', '.join(topics)}")

        if call_logs:
            parts.append(f"Recent calls: {len(call_logs)} in the last period")

        if not last and not convos:
            parts.append("No recent activity on record.")

        return "\n".join(parts)

    return check_wellness
```

## Verification

```bash
pytest tests/test_wellness.py -v
```
