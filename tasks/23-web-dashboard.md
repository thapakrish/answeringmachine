# Task 23: Web Dashboard (Stretch Goal)

- **Priority**: P2
- **Deps**: Task 02
- **PRD**: FR-7.1 through FR-7.5

## Objective

Create a FastAPI-based JSON API for managing families, members, messages, and call logs. This is a stretch goal for the hackathon demo.

## Tests First

```python
# tests/test_dashboard.py
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def app():
    from web.dashboard import app
    return app


@pytest.mark.asyncio
async def test_get_family(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family")
    assert resp.status_code in (200, 404)

@pytest.mark.asyncio
async def test_get_family_not_found(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_create_family(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/families", json={
            "family_id": "test_family",
            "name": "Test Family",
            "device_phones": ["+10000000000"],
            "passphrase": "test phrase",
        })
    assert resp.status_code in (200, 201)

@pytest.mark.asyncio
async def test_add_member(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/families/smith_family/members", json={
            "member_id": "member_test",
            "name": "Test",
            "role": "friend",
            "phone_numbers": ["+10000000001"],
            "is_device_user": False,
        })
    assert resp.status_code in (200, 201)

@pytest.mark.asyncio
async def test_get_messages(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family/messages")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

@pytest.mark.asyncio
async def test_get_call_logs(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family/call-logs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

## Implementation

```python
# web/dashboard.py
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
    refs = db.db.collection("families").document(family_id).collection("messages").order_by("created_at")
    return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]

@app.get("/api/families/{family_id}/call-logs")
async def get_call_logs(family_id: str):
    refs = db.db.collection("families").document(family_id).collection("call_logs").order_by("timestamp")
    return [{"id": doc.id, **doc.to_dict()} async for doc in refs.stream()]
```

## Verification

```bash
pytest tests/test_dashboard.py -v
uvicorn web.dashboard:app --port 8001  # Manual verification
```
