from typing import AsyncIterable

from line.agent import AgentClass, TurnEnv
from line.events import (
    AgentEndCall,
    AgentSendText,
    CallEnded,
    CallStarted,
    InputEvent,
    OutputEvent,
    UserTextSent,
)
from loguru import logger


class GatekeeperAgent(AgentClass):
    def __init__(self, metadata: dict, db):
        self._metadata = metadata
        self._db = db
        self._passphrase = None
        self._attempts = 0
        self._max_attempts = 2

    async def process(self, env: TurnEnv, event: InputEvent) -> AsyncIterable[OutputEvent]:
        if isinstance(event, CallStarted):
            logger.info(f"GatekeeperAgent: CallStarted for {self._metadata.get('caller_phone', 'unknown')}")
            try:
                self._passphrase = await self._db.get_passphrase(self._metadata["family_id"])
            except Exception as e:
                logger.error(f"GatekeeperAgent: failed to get passphrase: {e}")
                self._passphrase = None
            if not self._passphrase:
                yield AgentSendText(text="This number is not accepting calls from unregistered numbers. Goodbye.")
                yield AgentEndCall()
                return
            yield AgentSendText(text="Hello! This number uses a family passphrase for unregistered callers. Please say the family passphrase to continue.")
            return

        if isinstance(event, CallEnded):
            return

        if isinstance(event, UserTextSent):
            user_input = event.content.strip().lower()
            if self._passphrase and user_input == self._passphrase.lower():
                yield AgentSendText(text="Passphrase accepted! Connecting you now.")
                return

            self._attempts += 1
            if self._attempts >= self._max_attempts:
                await self._db.log_unknown_call(
                    phone=self._metadata.get("caller_phone", "unknown"),
                    device_phone=self._metadata.get("device_phone", "unknown"),
                    family_id=self._metadata["family_id"],
                )
                yield AgentSendText(text="Incorrect passphrase. This call has been logged. Goodbye.")
                yield AgentEndCall()
                return

            remaining = self._max_attempts - self._attempts
            yield AgentSendText(text=f"That's not correct. You have {remaining} attempt{'s' if remaining != 1 else ''} remaining. Please try again.")
