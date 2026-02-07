import pytest


@pytest.fixture
def sample_metadata():
    """Factory for call metadata dicts."""
    def _make(
        family_id="smith_family",
        member_id="member_rose",
        member_name="Rose",
        member_role="grandparent",
        is_device_user=True,
        is_authorized=True,
        is_guest=False,
    ):
        return {
            "family_id": family_id,
            "member_id": member_id,
            "member_name": member_name,
            "member_role": member_role,
            "is_device_user": is_device_user,
            "is_authorized": is_authorized,
            "is_guest": is_guest,
        }
    return _make
