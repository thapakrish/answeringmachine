from typing import Annotated

from line.llm_agent import ToolEnv, loopback_tool


def make_hear_messages(db, family_id, member_id):
    @loopback_tool
    async def hear_messages(ctx: ToolEnv) -> str:
        """Read all unread messages aloud. Call this when the user wants to hear their messages."""
        messages = await db.get_unread_messages(family_id, member_id)
        if not messages:
            return "You have no new messages."

        lines = []
        for msg in messages:
            lines.append(f"Message from {msg['from_name']}: {msg['content']}")

        msg_ids = [msg["id"] for msg in messages]
        await db.mark_messages_read(family_id, msg_ids)

        return "\n".join(lines)

    return hear_messages


def make_leave_message(db, family_id, from_member_id, from_name):
    @loopback_tool
    async def leave_message(
        ctx: ToolEnv,
        message_content: Annotated[str, "The message to leave for the device user"],
    ) -> str:
        """Leave a message for the device user. Call this when the caller wants to leave a message."""
        device_user = await db.get_primary_device_user(family_id)
        to_member_id = device_user["id"] if device_user else "unknown"

        await db.save_message(
            family_id=family_id,
            from_member_id=from_member_id,
            from_name=from_name,
            to_member_id=to_member_id,
            content=message_content,
        )
        return "Your message has been saved and will be delivered."

    return leave_message
