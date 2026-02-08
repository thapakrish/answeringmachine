import json
import os
from typing import AsyncIterable

import litellm
from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, CallEnded, CallStarted, InputEvent, OutputEvent, UserTextSent
from loguru import logger
from line.llm_agent import LlmAgent, LlmConfig, end_call, web_search

from agents.prompts import FAMILY_MEMBER_GREETER_PROMPT
from tools.language_tools import make_language_switch_tools
from tools.message_tools import make_leave_anonymous, make_leave_message
from tools.reminder_tools import make_add_reminder
from tools.search_tools import make_browse_website
from tools.wellness_tools import make_check_wellness


class FamilyMemberAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        is_guest = metadata.get("is_guest", False)

        leave_message = make_leave_message(db, metadata["family_id"], metadata["member_id"], metadata["member_name"])

        tools = [leave_message, end_call]

        if not is_guest:
            leave_anonymous = make_leave_anonymous(db, metadata["family_id"])
            add_reminder = make_add_reminder(db, metadata["family_id"], metadata["member_id"])
            check_wellness = make_check_wellness(db, metadata["family_id"])
            browse_website = make_browse_website()
            tools.extend([leave_anonymous, add_reminder, check_wellness, web_search, browse_website])

        device_user_name = "the device user"
        self._device_user_name = device_user_name

        # Create greeter first without language tools
        self._greeter = LlmAgent(
            model="anthropic/claude-haiku-4-5-20251001",
            api_key=self._api_key,
            tools=tools,
            config=LlmConfig(
                system_prompt=FAMILY_MEMBER_GREETER_PROMPT.format(
                    member_name=metadata["member_name"],
                    member_role=metadata["member_role"],
                    device_user_name=device_user_name,
                ),
            ),
        )

        # Now create language tools with greeter ref so they can update its system prompt
        language_tools = make_language_switch_tools(greeter_agent=self._greeter)
        self._greeter._tools.extend(language_tools)
        self.model_id = "anthropic/claude-haiku-4-5-20251001"
        self._input_history: list[InputEvent] = []

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def _load_memory_context(self):
        """Load caller's conversation memory into the system prompt."""
        family_id = self._metadata["family_id"]
        member_id = self._metadata["member_id"]
        if not member_id:
            return
        memory = await self._db.get_memory(family_id, member_id)

        convos = memory.get("recent_conversations", [])
        if not convos:
            return

        memory_lines = [f"- {c.get('summary', '')}" for c in convos[-5:]]
        memory_context = "\n".join(memory_lines)

        # Rebuild system prompt with memory context appended
        base_prompt = FAMILY_MEMBER_GREETER_PROMPT.format(
            member_name=self._metadata["member_name"],
            member_role=self._metadata["member_role"],
            device_user_name=self._device_user_name,
        )
        updated_prompt = base_prompt + f"\n\nRecent context from {self._metadata['member_name']}'s past calls:\n{memory_context}"

        config = LlmConfig(system_prompt=updated_prompt)
        self._greeter._config = config
        self._greeter._llm._config = config

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            logger.info(f"FamilyMemberAgent: CallStarted for {self._metadata.get('member_name')}")
            try:
                await self._load_memory_context()
            except Exception as e:
                logger.error(f"FamilyMemberAgent: memory load failed: {e}")
            name = self._metadata["member_name"]
            yield AgentSendText(text=f"Hi {name}! How can I help you today?")
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
            summary = data.get("summary", "Had a conversation")

            await self._db.log_call(
                family_id=self._metadata["family_id"],
                caller_phone=self._metadata.get("caller_phone", "unknown"),
                member_id=self._metadata.get("member_id", "unknown"),
                member_name=self._metadata["member_name"],
                summary=summary,
                is_anonymous=False,
            )

            if self._metadata.get("member_id"):
                await self._db.save_memory(
                    self._metadata["family_id"],
                    self._metadata["member_id"],
                    summary=summary,
                    topics=data.get("topics", []),
                    mood=data.get("mood", "neutral"),
                )
            logger.info(f"Logged call from {self._metadata['member_name']}: {summary}")
        except Exception as e:
            logger.error(f"Failed to log call: {e}")
