import os
from datetime import datetime
from typing import AsyncIterable

from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, CallEnded, CallStarted, InputEvent, OutputEvent
from line.llm_agent import LlmAgent, LlmConfig, agent_as_handoff, end_call

from agents.prompts import COMPANION_PROMPT, DEVICE_USER_GREETER_PROMPT
from tools.message_tools import make_hear_messages
from tools.reminder_tools import make_hear_reminders, make_set_reminder


async def _build_greeting(metadata, db):
    """Build a dynamic greeting with time-of-day, unread count, and memory."""
    name = metadata["member_name"]
    family_id = metadata["family_id"]
    member_id = metadata["member_id"]

    hour = datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 17:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"

    parts = [f"{time_greeting}, {name}!"]

    unread = await db.get_unread_messages(family_id, member_id)
    if unread:
        count = len(unread)
        parts.append(f"You have {count} new message{'s' if count != 1 else ''}.")

    memory = await db.get_memory(family_id, member_id)
    convos = memory.get("recent_conversations", [])
    if convos:
        last = convos[-1]
        parts.append(f"Last time we talked, you mentioned {last['summary'].lower()}.")

    parts.append("What would you like to do?")
    return " ".join(parts)


class DeviceUserAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")

        hear_messages = make_hear_messages(db, metadata["family_id"], metadata["member_id"])
        set_reminder = make_set_reminder(db, metadata["family_id"], metadata["member_id"])
        hear_reminders = make_hear_reminders(db, metadata["family_id"], metadata["member_id"])

        self._companion = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=[end_call],
            config=LlmConfig(
                system_prompt=COMPANION_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    preferences="",
                    memory_context="",
                ),
            ),
        )

        companion_chat = agent_as_handoff(
            self._companion,
            name="companion_chat",
            description="Transfer to companion chat mode for friendly conversation. Use when the user wants to chat, talk, or have a conversation.",
        )

        self._greeter = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=[hear_messages, hear_reminders, set_reminder, companion_chat, end_call],
            config=LlmConfig(
                system_prompt=DEVICE_USER_GREETER_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    preferences="",
                    memory_context="",
                ),
            ),
        )

        self.model_id = "anthropic/claude-haiku-4-5-20251001"

        # Conversation tracking for memory save on CallEnded
        self._conversation_summary = None
        self._conversation_topics = []
        self._conversation_mood = "neutral"

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            greeting = await _build_greeting(self._metadata, self._db)
            yield AgentSendText(text=greeting)
            return

        if isinstance(event, CallEnded):
            if self._conversation_summary:
                await self._db.save_memory(
                    self._metadata["family_id"],
                    self._metadata["member_id"],
                    summary=self._conversation_summary,
                    topics=self._conversation_topics,
                    mood=self._conversation_mood,
                )
            await self._greeter.cleanup()
            await self._companion.cleanup()
            return

        async for output in self._greeter.process(env, event):
            yield output
