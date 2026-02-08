import json
import os
from datetime import datetime
from typing import AsyncIterable

import litellm
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, AgentUpdateCall, CallEnded, CallStarted, InputEvent, OutputEvent, UserTextSent
from loguru import logger
from line.llm_agent import LlmAgent, LlmConfig, agent_as_handoff, end_call, web_search

from agents.prompts import COMPANION_PROMPT, DEVICE_USER_GREETER_PROMPT
from agents.role_config import get_role_config
from tools.message_tools import make_hear_messages
from tools.reminder_tools import make_hear_reminders, make_set_reminder
from tools.search_tools import make_browse_website


async def _build_greeting(metadata, db):
    """Build a dynamic greeting with time-of-day, unread count."""
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

    parts.append("What would you like to do?")
    return " ".join(parts)


class DeviceUserAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        self._role_config = get_role_config(metadata["member_role"])

        hear_messages = make_hear_messages(db, metadata["family_id"], metadata["member_id"])
        set_reminder = make_set_reminder(db, metadata["family_id"], metadata["member_id"])
        hear_reminders = make_hear_reminders(db, metadata["family_id"], metadata["member_id"])
        browse_website = make_browse_website()

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
            tools=[hear_messages, hear_reminders, set_reminder, web_search, browse_website, companion_chat, end_call],
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
        self._input_history: list[InputEvent] = []

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def _load_memory_context(self):
        """Load conversation memory into system prompts so the LLM knows past interactions."""
        family_id = self._metadata["family_id"]
        member_id = self._metadata["member_id"]
        memory = await self._db.get_memory(family_id, member_id)

        convos = memory.get("recent_conversations", [])
        if convos:
            memory_lines = [f"- {c.get('summary', '')}" for c in convos[-5:]]
            memory_context = "\n".join(memory_lines)
        else:
            memory_context = "No previous conversations."

        prefs = memory.get("preferences", {})
        preferences = ", ".join(prefs.get("interests", [])) if prefs else ""

        greeter_config = LlmConfig(
            system_prompt=DEVICE_USER_GREETER_PROMPT.format(
                member_name=self._metadata["member_name"],
                member_role=self._metadata["member_role"],
                preferences=preferences,
                memory_context=memory_context,
            ),
        )
        self._greeter._config = greeter_config
        self._greeter._llm._config = greeter_config

        companion_config = LlmConfig(
            system_prompt=COMPANION_PROMPT.format(
                member_name=self._metadata["member_name"],
                member_role=self._metadata["member_role"],
                preferences=preferences,
                memory_context=memory_context,
            ),
        )
        self._companion._config = companion_config
        self._companion._llm._config = companion_config

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            logger.info(f"DeviceUserAgent: CallStarted for {self._metadata.get('member_name')}")
            yield AgentUpdateCall(voice_id=self._role_config["voice_id"])
            try:
                await self._load_memory_context()
                greeting = await _build_greeting(self._metadata, self._db)
            except Exception as e:
                logger.error(f"DeviceUserAgent: greeting failed: {e}")
                greeting = f"Hello, {self._metadata.get('member_name', 'there')}! How can I help you today?"
            yield AgentSendText(text=greeting)
            return

        if isinstance(event, CallEnded):
            await self._save_conversation_memory()
            await self._greeter.cleanup()
            await self._companion.cleanup()
            return

        self._input_history.append(event)
        async for output in self._greeter.process(env, event):
            yield output

    async def _save_conversation_memory(self):
        """Summarize the conversation and save to Firestore."""
        try:
            lines = []
            for ev in self._input_history:
                if isinstance(ev, UserTextSent):
                    lines.append(f"User: {ev.content}")

            agent_parts = []
            for _, ev in self._greeter._local_history:
                if isinstance(ev, AgentSendText):
                    agent_parts.append(ev.text)
                elif agent_parts:
                    lines.append(f"Agent: {''.join(agent_parts).strip()}")
                    agent_parts = []
            if agent_parts:
                lines.append(f"Agent: {''.join(agent_parts).strip()}")

            if not lines:
                return

            transcript = "\n".join(lines)
            response = await litellm.acompletion(
                model="anthropic/claude-haiku-4-5-20251001",
                api_key=self._api_key,
                messages=[{
                    "role": "user",
                    "content": f"Summarize this phone conversation in 2-3 sentences. Extract: topics (keywords) and mood (one word). Return JSON: {{\"summary\": \"...\", \"topics\": [...], \"mood\": \"...\"}}\n\n{transcript}",
                }],
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)

            await self._db.save_memory(
                self._metadata["family_id"],
                self._metadata["member_id"],
                summary=data.get("summary", "Had a conversation"),
                topics=data.get("topics", []),
                mood=data.get("mood", "neutral"),
            )
            logger.info(f"Saved conversation memory: {data.get('summary', '')[:80]}")
        except Exception as e:
            logger.error(f"Failed to save conversation memory: {e}")
