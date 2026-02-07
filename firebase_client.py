import json
import os
from datetime import datetime
from google.cloud.firestore import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter
from google.oauth2 import service_account
from google.cloud.firestore import SERVER_TIMESTAMP
from loguru import logger


class FirebaseClient:
    def __init__(self):
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            info = json.loads(sa_json)
            creds = service_account.Credentials.from_service_account_info(info)
        else:
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
            creds = service_account.Credentials.from_service_account_file(cred_path)
        self.db = AsyncClient(credentials=creds, project=creds.project_id)

    async def find_family_by_device_phone(self, phone: str) -> dict | None:
        """Find family by device phone number."""
        query = self.db.collection("families").where(
            filter=FieldFilter("device_phones", "array_contains", phone)
        )
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def find_member_by_phone(self, family_id: str, phone: str) -> dict | None:
        """Find member in family by phone number."""
        query = (
            self.db.collection("families").document(family_id)
            .collection("members")
            .where(filter=FieldFilter("phone_numbers", "array_contains", phone))
        )
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def get_primary_device_user(self, family_id: str) -> dict | None:
        """Get the primary device user in a family."""
        query = (
            self.db.collection("families").document(family_id)
            .collection("members")
            .where(filter=FieldFilter("is_device_user", "==", True))
        )
        docs = [doc async for doc in query.stream()]
        if docs:
            return {"id": docs[0].id, **docs[0].to_dict()}
        return None

    async def get_passphrase(self, family_id: str) -> str | None:
        """Get family passphrase (field on family document)."""
        doc = await self.db.collection("families").document(family_id).get()
        if doc.exists:
            return doc.to_dict().get("passphrase")
        return None

    async def save_message(self, family_id: str, from_member_id: str, from_name: str, to_member_id: str, content: str) -> str:
        """Save a message to a family's messages subcollection."""
        ref = self.db.collection("families").document(family_id).collection("messages").document()
        await ref.set({
            "from_member_id": from_member_id,
            "from_name": from_name,
            "to_member_id": to_member_id,
            "content": content,
            "read": False,
            "created_at": SERVER_TIMESTAMP,
        })
        return ref.id

    async def get_unread_messages(self, family_id: str, member_id: str) -> list[dict]:
        """Get unread messages for a member, sorted by creation time."""
        msgs_ref = (
            self.db.collection("families").document(family_id).collection("messages")
            .where(filter=FieldFilter("to_member_id", "==", member_id))
            .where(filter=FieldFilter("read", "==", False))
        )
        results = [{"id": doc.id, **doc.to_dict()} async for doc in msgs_ref.stream()]
        results.sort(key=lambda m: m.get("created_at") or 0)
        return results

    async def mark_messages_read(self, family_id: str, message_ids: list[str]):
        """Mark messages as read."""
        for msg_id in message_ids:
            ref = self.db.collection("families").document(family_id).collection("messages").document(msg_id)
            await ref.update({"read": True})

    async def get_memory(self, family_id: str, member_id: str) -> dict:
        """Get conversation memory for a member."""
        doc = await (
            self.db.collection("families").document(family_id)
            .collection("memory").document(member_id).get()
        )
        if not doc.exists:
            return {"recent_conversations": [], "preferences": {}, "last_interaction": None}
        return doc.to_dict()

    async def save_memory(self, family_id: str, member_id: str, summary: str, topics: list, mood: str):
        """Save a conversation summary to memory, capped at 20 entries."""
        ref = self.db.collection("families").document(family_id).collection("memory").document(member_id)
        doc = await ref.get()

        now = datetime.now().isoformat()
        entry = {"date": now, "summary": summary, "topics": topics, "mood": mood}

        if doc.exists:
            data = doc.to_dict()
            convos = data.get("recent_conversations", [])
            convos.append(entry)
            convos = convos[-20:]
            await ref.update({
                "recent_conversations": convos,
                "last_interaction": now,
            })
        else:
            await ref.set({
                "recent_conversations": [entry],
                "preferences": {},
                "last_interaction": now,
            })

    async def log_unknown_call(self, phone: str, device_phone: str, family_id: str):
        """Log an unknown caller attempt."""
        ref = self.db.collection("unknown_call_attempts").document()
        await ref.set({
            "phone_number": phone,
            "target_device_phone": device_phone,
            "family_id": family_id,
            "timestamp": SERVER_TIMESTAMP,
            "blocked": True,
        })

    async def save_reminder(self, family_id: str, for_member_id: str, created_by_id: str, content: str, time_str: str, recurring: bool) -> str:
        """Save a reminder for a member."""
        ref = self.db.collection("families").document(family_id).collection("reminders").document()
        await ref.set({
            "for_member_id": for_member_id,
            "created_by_member_id": created_by_id,
            "content": content,
            "time": time_str,
            "recurring": recurring,
            "active": True,
            "created_at": SERVER_TIMESTAMP,
        })
        return ref.id

    async def get_reminders(self, family_id: str, member_id: str) -> list[dict]:
        """Get active reminders for a member."""
        refs = (
            self.db.collection("families").document(family_id).collection("reminders")
            .where(filter=FieldFilter("for_member_id", "==", member_id))
            .where(filter=FieldFilter("active", "==", True))
        )
        return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]

    async def get_recent_call_logs(self, family_id: str, limit: int = 5) -> list[dict]:
        """Get recent call logs for a family."""
        refs = self.db.collection("families").document(family_id).collection("call_logs").limit(limit)
        return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]

    async def log_call(self, family_id: str, caller_phone: str, member_id: str, member_name: str, summary: str, is_anonymous: bool):
        """Log a call in the family's call log."""
        ref = self.db.collection("families").document(family_id).collection("call_logs").document()
        await ref.set({
            "caller_phone": caller_phone,
            "caller_member_id": member_id,
            "caller_name": member_name,
            "timestamp": SERVER_TIMESTAMP,
            "summary": summary,
            "is_anonymous": is_anonymous,
        })
