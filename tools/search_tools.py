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
        """Browse a real website to find specific information. Use for checking library hours, community center events, local business info, restaurant menus, or any webpage content. This takes a moment to look up."""
        yield "Let me look that up for you..."

        try:
            from stagehand import AsyncStagehand

            stagehand = AsyncStagehand(
                browserbase_api_key=os.environ.get("BROWSERBASE_API_KEY"),
                browserbase_project_id=os.environ.get("BROWSERBASE_PROJECT_ID"),
                model_api_key=os.environ.get("GEMINI_API_KEY"),
            )
            session = await stagehand.sessions.create(model_name="google/gemini-2.0-flash")

            yield "Opening the website now..."

            await session.navigate(url=url)

            # Try clicking through cookie banners or popups that might block content
            try:
                await session.act(input="If there is a cookie consent banner or popup, dismiss or accept it")
            except Exception:
                pass

            result = await session.extract(
                instruction=f"Extract the following information from this page: {query}. Be thorough and include relevant details like dates, times, addresses, and phone numbers if available.",
            )

            await session.end()

            if result:
                yield f"Here's what I found: {result}"
            else:
                yield "I opened the page but couldn't find the specific information you asked about."

        except Exception as e:
            yield f"I wasn't able to look that up right now. Let me try a web search instead."

    return browse_website
