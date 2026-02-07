import os
from dotenv import load_dotenv

load_dotenv()

from line.voice_agent_app import PreCallResult, VoiceAgentApp


def make_pre_call_handler(db):
    """Factory that creates pre_call_handler with injected db."""
    async def pre_call_handler(call_request):
        family = await db.find_family_by_device_phone(call_request.to)
        if not family:
            return None

        caller_phone = call_request.from_
        is_device_user = caller_phone in family.get("device_phones", [])

        if is_device_user:
            member = await db.get_primary_device_user(family["id"])
        else:
            member = await db.find_member_by_phone(family["id"], caller_phone)

        if not member and not is_device_user:
            return PreCallResult(metadata={
                "family_id": family["id"],
                "family_name": family["name"],
                "member_id": None,
                "member_name": "there",
                "member_role": "unknown",
                "is_device_user": False,
                "is_authorized": False,
                "caller_phone": caller_phone,
                "device_phone": call_request.to,
            })

        return PreCallResult(metadata={
            "family_id": family["id"],
            "family_name": family["name"],
            "member_id": member["id"],
            "member_name": member["name"],
            "member_role": member.get("role", "unknown"),
            "is_device_user": is_device_user,
            "is_authorized": True,
            "caller_phone": caller_phone,
            "device_phone": call_request.to,
        })
    return pre_call_handler


def make_get_agent(db):
    """Factory that creates get_agent with injected db."""
    async def get_agent(env, call_request):
        from agents.device_user_agent import DeviceUserAgent
        from agents.family_member_agent import FamilyMemberAgent
        from agents.gatekeeper_agent import GatekeeperAgent

        metadata = call_request.metadata or {}
        if not metadata.get("is_authorized", True):
            return GatekeeperAgent(metadata=metadata, db=db)
        if metadata.get("is_device_user", False):
            return DeviceUserAgent(metadata=metadata, db=db)
        return FamilyMemberAgent(metadata=metadata, db=db)
    return get_agent


from firebase_client import FirebaseClient

db = FirebaseClient()

app = VoiceAgentApp(
    get_agent=make_get_agent(db),
    pre_call_handler=make_pre_call_handler(db),
)

if __name__ == "__main__":
    print("AnsweringMachine is running")
    app.run()
