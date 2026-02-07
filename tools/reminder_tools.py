from typing import Annotated

from line.llm_agent import ToolEnv, loopback_tool


def make_set_reminder(db, family_id, member_id):
    @loopback_tool
    async def set_reminder(
        ctx: ToolEnv,
        content: Annotated[str, "What to remember"],
        time: Annotated[str, "When to be reminded, e.g. '9:00 AM' or '3:00 PM daily'"],
    ) -> str:
        """Set a reminder for yourself. Provide what to remember and when."""
        await db.save_reminder(family_id, member_id, member_id, content, time, False)
        return f"Reminder set: '{content}' at {time}."

    return set_reminder


def make_hear_reminders(db, family_id, member_id):
    @loopback_tool
    async def hear_reminders(ctx: ToolEnv) -> str:
        """Read all active reminders aloud."""
        reminders = await db.get_reminders(family_id, member_id)
        if not reminders:
            return "You have no active reminders."
        lines = []
        for rem in reminders:
            lines.append(f"Reminder: {rem['content']} at {rem['time']}")
        return "\n".join(lines)

    return hear_reminders


def make_add_reminder(db, family_id, from_member_id):
    @loopback_tool
    async def add_reminder(
        ctx: ToolEnv,
        content: Annotated[str, "What to remind about"],
        time: Annotated[str, "When to remind, e.g. '9:00 AM' or 'every morning'"],
    ) -> str:
        """Add a reminder for the device user. Provide what to remind about and when."""
        device_user = await db.get_primary_device_user(family_id)
        for_member_id = device_user["id"] if device_user else "unknown"
        await db.save_reminder(family_id, for_member_id, from_member_id, content, time, False)
        return f"Reminder added for {device_user['name']}: '{content}' at {time}."

    return add_reminder
