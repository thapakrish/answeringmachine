"""Seed Firestore with demo Smith family. Idempotent: uses fixed document IDs."""

import asyncio
from firebase_client import FirebaseClient

FAMILY_ID = "smith_family"

FAMILY = {
    "name": "The Smiths",
    "device_phones": ["+15551234567"],
    "passphrase": "sunflower garden",
}

MEMBERS = {
    "member_rose": {
        "name": "Rose",
        "role": "grandparent",
        "phone_numbers": ["+15551234567"],
        "is_device_user": True,
        "preferences": {"interests": ["mystery novels", "gardening"]},
    },
    "member_sarah": {
        "name": "Sarah",
        "role": "granddaughter",
        "phone_numbers": ["+15559876543"],
        "is_device_user": False,
        "preferences": {},
    },
    "member_mike": {
        "name": "Mike",
        "role": "son",
        "phone_numbers": ["+15551111111"],
        "is_device_user": False,
        "preferences": {},
    },
    "member_emma": {
        "name": "Emma",
        "role": "great-granddaughter",
        "phone_numbers": ["+15552222222"],
        "is_device_user": False,
        "preferences": {},
    },
}

MESSAGES = {
    "msg_sarah_1": {
        "from_member_id": "member_sarah",
        "from_name": "Sarah",
        "to_member_id": "member_rose",
        "content": "Hi Grandma! Just wanted to let you know I'll visit on Sunday. Love you!",
        "read": False,
    },
    "msg_mike_1": {
        "from_member_id": "member_mike",
        "from_name": "Mike",
        "to_member_id": "member_rose",
        "content": "Mom, don't forget your doctor appointment is on Tuesday at 2pm.",
        "read": False,
    },
}

REMINDERS = {
    "rem_medicine": {
        "for_member_id": "member_rose",
        "created_by_member_id": "member_mike",
        "content": "Take morning medicine",
        "time": "9:00 AM",
        "recurring": True,
        "active": True,
    },
    "rem_doctor": {
        "for_member_id": "member_rose",
        "created_by_member_id": "member_sarah",
        "content": "Doctor appointment",
        "time": "2:00 PM Tuesday",
        "recurring": False,
        "active": True,
    },
}

MEMORY = {
    "member_rose": {
        "recent_conversations": [
            {
                "date": "2025-01-15",
                "summary": "Rose talked about finishing a mystery novel and wanting to start a new one",
                "topics": ["mystery novels", "reading"],
                "mood": "happy",
            },
            {
                "date": "2025-01-14",
                "summary": "Rose asked about the weather for gardening and set a reminder for watering plants",
                "topics": ["gardening", "weather"],
                "mood": "content",
            },
        ],
        "preferences": {"interests": ["mystery novels", "gardening"]},
        "last_interaction": "2025-01-15T10:30:00",
    }
}


async def seed():
    db = FirebaseClient()
    family_ref = db.db.collection("families").document(FAMILY_ID)

    # Family document
    await family_ref.set(FAMILY)

    # Members
    for member_id, data in MEMBERS.items():
        await family_ref.collection("members").document(member_id).set(data)

    # Messages
    for msg_id, data in MESSAGES.items():
        await family_ref.collection("messages").document(msg_id).set(data)

    # Reminders
    for rem_id, data in REMINDERS.items():
        await family_ref.collection("reminders").document(rem_id).set(data)

    # Memory
    for member_id, data in MEMORY.items():
        await family_ref.collection("memory").document(member_id).set(data)

    print(f"Seeded family '{FAMILY_ID}' with {len(MEMBERS)} members, {len(MESSAGES)} messages, {len(REMINDERS)} reminders")


if __name__ == "__main__":
    asyncio.run(seed())
