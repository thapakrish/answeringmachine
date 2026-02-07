from line.llm_agent import ToolEnv, loopback_tool


def make_check_wellness(db, family_id):
    @loopback_tool
    async def check_wellness(ctx: ToolEnv) -> str:
        """Check on the device user's recent activity, mood, and interactions. Shows when they last used the device and what they talked about."""
        device_user = await db.get_primary_device_user(family_id)
        member_id = device_user["id"]

        memory = await db.get_memory(family_id, member_id)
        call_logs = await db.get_recent_call_logs(family_id, limit=5)

        parts = [f"Wellness check for {device_user['name']}:"]

        last = memory.get("last_interaction")
        if last:
            parts.append(f"Last interaction: {last}")

        convos = memory.get("recent_conversations", [])
        if convos:
            recent = convos[-1]
            parts.append(f"Last conversation: {recent['summary']}")
            parts.append(f"Mood: {recent.get('mood', 'unknown')}")
            topics = recent.get("topics", [])
            if topics:
                parts.append(f"Topics: {', '.join(topics)}")

        if call_logs:
            parts.append(f"Recent calls: {len(call_logs)} in the last period")

        if not last and not convos:
            parts.append("No recent activity on record.")

        return "\n".join(parts)

    return check_wellness
