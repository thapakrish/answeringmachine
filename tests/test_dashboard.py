import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_db():
    db = MagicMock()
    # Mock the Firestore collection/document chain
    mock_doc_ref = AsyncMock()
    mock_collection_ref = AsyncMock()

    db.db = MagicMock()
    return db


@pytest.fixture
def app(mock_db):
    with patch("web.dashboard.db", mock_db):
        from web.dashboard import app
        yield app


@pytest.mark.asyncio
async def test_get_family(app, mock_db):
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.id = "smith_family"
    mock_doc.to_dict.return_value = {"name": "The Smiths", "device_phones": ["+15551234567"]}

    mock_db.db.collection.return_value.document.return_value.get = AsyncMock(return_value=mock_doc)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "smith_family"
    assert data["name"] == "The Smiths"


@pytest.mark.asyncio
async def test_get_family_not_found(app, mock_db):
    mock_doc = MagicMock()
    mock_doc.exists = False

    mock_db.db.collection.return_value.document.return_value.get = AsyncMock(return_value=mock_doc)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_family(app, mock_db):
    mock_db.db.collection.return_value.document.return_value.set = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/families", json={
            "family_id": "test_family",
            "name": "Test Family",
            "device_phones": ["+10000000000"],
            "passphrase": "test phrase",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "test_family"


@pytest.mark.asyncio
async def test_add_member(app, mock_db):
    mock_db.db.collection.return_value.document.return_value.collection.return_value.document.return_value.set = AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/families/smith_family/members", json={
            "member_id": "member_test",
            "name": "Test",
            "role": "friend",
            "phone_numbers": ["+10000000001"],
            "is_device_user": False,
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "member_test"


@pytest.mark.asyncio
async def test_get_messages(app, mock_db):
    mock_msg = MagicMock()
    mock_msg.id = "msg1"
    mock_msg.to_dict.return_value = {"from_name": "Sarah", "content": "Hello!"}

    async def mock_stream():
        yield mock_msg

    mock_db.db.collection.return_value.document.return_value.collection.return_value.stream = mock_stream

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["from_name"] == "Sarah"


@pytest.mark.asyncio
async def test_get_call_logs(app, mock_db):
    mock_log = MagicMock()
    mock_log.id = "log1"
    mock_log.to_dict.return_value = {"caller_name": "Sarah", "summary": "Left a message"}

    async def mock_stream():
        yield mock_log

    mock_db.db.collection.return_value.document.return_value.collection.return_value.stream = mock_stream

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/families/smith_family/call-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["caller_name"] == "Sarah"
