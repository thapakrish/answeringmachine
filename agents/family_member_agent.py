import os
from typing import AsyncIterable

from line.agent import AgentClass, TurnEnv
from line.events import AgentSendText, CallEnded, CallStarted, InputEvent, OutputEvent
from line.llm_agent import LlmAgent, LlmConfig, end_call

from agents.prompts import FAMILY_MEMBER_GREETER_PROMPT
from tools.message_tools import make_leave_anonymous, make_leave_message
from tools.reminder_tools import make_add_reminder
from tools.wellness_tools import make_check_wellness


class FamilyMemberAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._api_key = os.getenv("ANTHROPIC_API_KEY")
        is_guest = metadata.get("is_guest", False)

        leave_message = make_leave_message(db, metadata["family_id"], metadata["member_id"], metadata["member_name"])

        # Build tool list based on guest status
        # All callers (including guests) can leave messages + end call
        tools = [leave_message, end_call]

        # Non-guests get additional tools
        if not is_guest:
            leave_anonymous = make_leave_anonymous(db, metadata["family_id"])
            add_reminder = make_add_reminder(db, metadata["family_id"], metadata["member_id"])
            check_wellness = make_check_wellness(db, metadata["family_id"])
            tools.extend([leave_anonymous, add_reminder, check_wellness])

        device_user_name = "the device user"

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
        self.model_id = "anthropic/claude-haiku-4-5-20251001"

    def tool_names(self) -> list[str]:
        return [t.__name__ if callable(t) else str(t) for t in self._greeter._tools]

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            name = self._metadata["member_name"]
            yield AgentSendText(text=f"Hi {name}! How can I help you today?")
            return

        if isinstance(event, CallEnded):
            await self._greeter.cleanup()
            return

        async for output in self._greeter.process(env, event):
            yield output
