from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from firebase_client import FirebaseClient

app = FastAPI(title="AnsweringMachine Dashboard")
db = FirebaseClient()


class FamilyCreate(BaseModel):
    family_id: str
    name: str
    device_phones: list[str]
    passphrase: str


class MemberCreate(BaseModel):
    member_id: str
    name: str
    role: str
    phone_numbers: list[str]
    is_device_user: bool = False


@app.get("/api/families/{family_id}")
async def get_family(family_id: str):
    doc = await db.db.collection("families").document(family_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Family not found")
    return {"id": doc.id, **doc.to_dict()}


@app.post("/api/families", status_code=201)
async def create_family(family: FamilyCreate):
    ref = db.db.collection("families").document(family.family_id)
    await ref.set({
        "name": family.name,
        "device_phones": family.device_phones,
        "passphrase": family.passphrase,
    })
    return {"id": family.family_id, "name": family.name}


@app.post("/api/families/{family_id}/members", status_code=201)
async def add_member(family_id: str, member: MemberCreate):
    ref = db.db.collection("families").document(family_id).collection("members").document(member.member_id)
    await ref.set({
        "name": member.name,
        "role": member.role,
        "phone_numbers": member.phone_numbers,
        "is_device_user": member.is_device_user,
    })
    return {"id": member.member_id, "name": member.name}


@app.get("/api/families/{family_id}/messages")
async def get_messages(family_id: str):
    refs = db.db.collection("families").document(family_id).collection("messages")
    results = [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]
    return results


@app.get("/api/families/{family_id}/call-logs")
async def get_call_logs(family_id: str):
    refs = db.db.collection("families").document(family_id).collection("call_logs")
    results = [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]
    return results
