import json
import os
from typing import AsyncIterable

import litellm
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, AgentToolCalled, AgentToolReturned, AgentUpdateCall, CallEnded, CallStarted, InputEvent, OutputEvent, UserTextSent
from line.llm_agent import LlmAgent, LlmConfig, end_call, web_search
from loguru import logger

from agents.prompts import FAMILY_MEMBER_GREETER_PROMPT
from agents.role_config import get_role_config
from tools.message_tools import make_leave_anonymous, make_leave_message
from tools.reminder_tools import make_add_reminder
from tools.search_tools import make_browse_website
from tools.wellness_tools import make_check_wellness


async def _build_family_greeting(metadata, db):
    """Build a greeting for family members that references past calls."""
    name = metadata["member_name"]
    family_id = metadata["family_id"]
    member_id = metadata["member_id"]

    parts = [f"Hi {name}!", "How can I help you today?"]
    return " ".join(parts)


class FamilyMemberAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        is_guest = metadata.get("is_guest", False)
        self._role_config = get_role_config("guest" if is_guest else metadata["member_role"])

        leave_message = make_leave_message(db, metadata["family_id"], metadata["member_id"], metadata["member_name"])

        # Build tool list based on guest status
        # All callers (including guests) can leave messages + end call
        tools = [leave_message, end_call]

        # Non-guests get additional tools
        if not is_guest:
            leave_anonymous = make_leave_anonymous(db, metadata["family_id"])
            add_reminder = make_add_reminder(db, metadata["family_id"], metadata["member_id"])
            check_wellness = make_check_wellness(db, metadata["family_id"])
            browse_website = make_browse_website()
            tools.extend([leave_anonymous, add_reminder, check_wellness, web_search, browse_website])

        device_user_name = "the device user"

        self._device_user_name = device_user_name
        self._greeter = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=tools,
            config=LlmConfig(
                system_prompt=FAMILY_MEMBER_GREETER_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    device_user_name=device_user_name,
                    personality=self._role_config["personality"],
                    memory_context="No previous conversations.",
                ),
            ),
        )
        self.model_id = "anthropic/claude-haiku-4-5-20251001"
        self._input_history: list[InputEvent] = []

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def _load_memory_context(self):
        """Load memory from DB and update system prompt with real context."""
        family_id = self._metadata["family_id"]
        member_id = self._metadata["member_id"]
        memory = await self._db.get_memory(family_id, member_id)

        convos = memory.get("recent_conversations", [])
        if convos:
            memory_lines = [f"- {c.get('summary', '')}" for c in convos[-5:]]
            memory_context = "\n".join(memory_lines)
        else:
            memory_context = "No previous conversations."

        greeter_config = LlmConfig(
            system_prompt=FAMILY_MEMBER_GREETER_PROMPT.format(
                member_name=self._metadata["member_name"],
                member_role=self._metadata["member_role"],
                device_user_name=self._device_user_name,
                personality=self._role_config["personality"],
                memory_context=memory_context,
            ),
        )
        self._greeter._config = greeter_config
        self._greeter._llm._config = greeter_config

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            yield AgentUpdateCall(voice_id=self._role_config["voice_id"])
            await self._load_memory_context()
            greeting = await _build_family_greeting(self._metadata, self._db)
            yield AgentSendText(text=greeting)
            return

        if isinstance(event, CallEnded):
            await self._save_call_log()
            await self._greeter.cleanup()
            return

        self._input_history.append(event)
        async for output in self._greeter.process(env, event):
            yield output

    async def _save_call_log(self):
        """Summarize the call, log it, and save conversation memory."""
        try:
            lines = []
            for ev in self._input_history:
                if isinstance(ev, UserTextSent):
                    lines.append(f"Caller: {ev.content}")

            # Concatenate streamed agent text chunks into complete messages
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
                    "content": f"Summarize this phone conversation in 2-3 sentences capturing key details, requests, and context that would be useful to remember for future calls. Also extract: topics (list of keywords) and mood (one word). Return JSON only: {{\"summary\": \"...\", \"topics\": [...], \"mood\": \"...\"}}\n\n{transcript}",
                }],
                max_tokens=300,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            summary = data.get("summary", "Had a conversation")

            await self._db.log_call(
                family_id=self._metadata["family_id"],
                caller_phone=self._metadata.get("caller_phone", "unknown"),
                member_id=self._metadata.get("member_id", "unknown"),
                member_name=self._metadata["member_name"],
                summary=summary,
                is_anonymous=False,
            )

            await self._db.save_memory(
                self._metadata["family_id"],
                self._metadata["member_id"],
                summary=summary,
                topics=data.get("topics", []),
                mood=data.get("mood", "neutral"),
                transcript=transcript,
            )
            logger.info(f"Logged call from {self._metadata['member_name']}: {summary}")
        except Exception as e:
            logger.error(f"Failed to log call: {e}")
