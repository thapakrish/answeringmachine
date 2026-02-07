import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def set_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def make_call_request():
    def _make(metadata):
        req = MagicMock()
        req.metadata = metadata
        return req
    return _make


@pytest.mark.asyncio
async def test_device_user_gets_device_user_agent(mock_db, make_call_request):
    from main import make_get_agent
    from agents.device_user_agent import DeviceUserAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": True, "is_authorized": True, "family_id": "f1", "member_id": "m1", "member_name": "Rose", "member_role": "grandparent"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, DeviceUserAgent)


@pytest.mark.asyncio
async def test_family_member_gets_family_member_agent(mock_db, make_call_request):
    from main import make_get_agent
    from agents.family_member_agent import FamilyMemberAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": False, "is_authorized": True, "family_id": "f1", "member_id": "m2", "member_name": "Sarah", "member_role": "granddaughter"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, FamilyMemberAgent)


@pytest.mark.asyncio
async def test_unauthorized_gets_gatekeeper(mock_db, make_call_request):
    from main import make_get_agent
    from agents.gatekeeper_agent import GatekeeperAgent
    get_agent = make_get_agent(mock_db)
    metadata = {"is_device_user": False, "is_authorized": False, "family_id": "f1", "member_id": None, "member_name": "there", "member_role": "unknown"}
    agent = await get_agent(MagicMock(), make_call_request(metadata))
    assert isinstance(agent, GatekeeperAgent)
