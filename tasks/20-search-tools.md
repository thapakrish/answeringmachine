# Task 20: Search Tools (quick_search + browse_website)

- **Priority**: P1 (quick_search) / P2 (browse_website)
- **Deps**: Task 07
- **PRD**: FR-2.7, FR-2.8

## Objective

Add two search capabilities to DeviceUserAgent:
1. `quick_search` — uses built-in `web_search` (DuckDuckGo) for weather, facts, quick answers
2. `browse_website` — uses Browserbase/Stagehand for navigating real websites (library, community center). Background tool.

## Tests First

```python
# tests/test_search_tools.py
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


# --- quick_search (web_search) ---

def test_quick_search_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("web_search" in name or "quick_search" in name for name in tool_names)

# --- browse_website (Browserbase) ---

def test_browse_website_tool_on_agent(metadata, mock_db):
    from agents.device_user_agent import DeviceUserAgent
    agent = DeviceUserAgent(metadata=metadata, db=mock_db)
    tool_names = agent.tool_names()
    assert any("browse_website" in name for name in tool_names)

@pytest.mark.asyncio
async def test_browse_website_yields_acknowledgment():
    from tools.search_tools import make_browse_website
    browse_website = make_browse_website()
    # The tool should be an async generator that first yields an acknowledgment
    results = []
    async for chunk in browse_website(url="https://example.com", query="hours"):
        results.append(chunk)
        break  # Just check the first yield
    assert len(results) >= 1
    assert "look" in results[0].lower() or "search" in results[0].lower()
```

## Implementation

```python
# tools/search_tools.py
import os
from line.llm_agent import loopback_tool, web_search

# quick_search: Just use the built-in web_search tool from Line SDK.
# Add it directly to the DeviceUserAgent greeter tools list.

# browse_website: Browserbase + Stagehand integration
def make_browse_website():
    @loopback_tool(is_background=True)
    async def browse_website(url: str, query: str):
        """Navigate to a website and find specific information. Use for library hours, community center events, local business info. This takes a moment to look up."""
        yield "Let me look that up for you..."

        try:
            from browserbase import Browserbase
            from stagehand import Stagehand

            bb = Browserbase(api_key=os.getenv("BROWSERBASE_API_KEY"))
            session = bb.sessions.create(project_id=os.getenv("BROWSERBASE_PROJECT_ID"))

            stagehand = Stagehand(
                api_key=os.getenv("GEMINI_API_KEY"),
                browser_base_session_id=session.id,
                model=os.getenv("STAGEHAND_MODEL", "gemini-1.5-pro"),
            )
            await stagehand.init()

            page = stagehand.page
            await page.goto(url)

            result = await stagehand.extract(f"Find information about: {query}")

            await stagehand.close()

            yield f"Here's what I found: {result}"
        except Exception as e:
            yield f"I wasn't able to look that up right now. The website might be unavailable."

    return browse_website
```

## Notes

- `web_search` is a built-in from Line SDK — just add to tools list, no wrapping needed.
- `browse_website` is a **background loopback tool** (`is_background=True`). It yields an immediate acknowledgment ("Let me look that up...") then delivers results when ready.
- Browserbase API key and project ID must be in `.env`.
- This is a P2 stretch goal — if Browserbase isn't available, the agent still works with `web_search`.

## Verification

```bash
pytest tests/test_search_tools.py -v
```
