import os
from typing import Annotated, AsyncIterable

from line.llm_agent import ToolEnv, loopback_tool


def make_browse_website():
    @loopback_tool(is_background=True)
    async def browse_website(
        ctx: ToolEnv,
        url: Annotated[str, "The website URL to navigate to"],
        query: Annotated[str, "What information to find on the website"],
    ) -> AsyncIterable[str]:
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
        except Exception:
            yield "I wasn't able to look that up right now. The website might be unavailable."

    return browse_website
