import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.find_family_by_device_phone = AsyncMock(return_value={
        "id": "smith_family",
        "name": "The Smiths",
        "device_phones": ["+15551234567"],
        "passphrase": "sunflower garden",
    })
    db.find_member_by_phone = AsyncMock(return_value={
        "id": "member_sarah",
        "name": "Sarah",
        "role": "granddaughter",
        "is_device_user": False,
    })
    db.get_primary_device_user = AsyncMock(return_value={
        "id": "member_rose",
        "name": "Rose",
        "role": "grandparent",
        "is_device_user": True,
    })
    return db


@pytest.fixture
def make_call_request():
    def _make(from_="+15559876543", to="+15551234567"):
        req = MagicMock()
        req.from_ = from_
        req.to = to
        req.metadata = {}
        return req
    return _make


@pytest.mark.asyncio
async def test_family_member_identified(mock_db, make_call_request):
    from main import make_pre_call_handler
    handler = make_pre_call_handler(mock_db)
    result = await handler(make_call_request(from_="+15559876543"))
    assert result is not None
    assert result.metadata["member_name"] == "Sarah"
    assert result.metadata["is_device_user"] is False
    assert result.metadata["is_authorized"] is True


@pytest.mark.asyncio
async def test_device_user_identified(mock_db, make_call_request):
    from main import make_pre_call_handler
    handler = make_pre_call_handler(mock_db)
    result = await handler(make_call_request(from_="+15551234567"))
    assert result is not None
    assert result.metadata["is_device_user"] is True
    assert result.metadata["member_name"] == "Rose"


@pytest.mark.asyncio
async def test_unknown_caller_flagged(mock_db, make_call_request):
    mock_db.find_member_by_phone = AsyncMock(return_value=None)
    from main import make_pre_call_handler
    handler = make_pre_call_handler(mock_db)
    result = await handler(make_call_request(from_="+19999999999"))
    assert result is not None
    assert result.metadata["is_authorized"] is False


@pytest.mark.asyncio
async def test_no_family_returns_none(mock_db, make_call_request):
    mock_db.find_family_by_device_phone = AsyncMock(return_value=None)
    from main import make_pre_call_handler
    handler = make_pre_call_handler(mock_db)
    result = await handler(make_call_request(to="+19999999999"))
    assert result is None


@pytest.mark.asyncio
async def test_metadata_has_required_fields(mock_db, make_call_request):
    from main import make_pre_call_handler
    handler = make_pre_call_handler(mock_db)
    result = await handler(make_call_request())
    required = [
        "family_id",
        "member_id",
        "member_name",
        "member_role",
        "is_device_user",
        "is_authorized",
        "caller_phone",
        "device_phone",
    ]
    for field in required:
        assert field in result.metadata, f"Missing field: {field}"
