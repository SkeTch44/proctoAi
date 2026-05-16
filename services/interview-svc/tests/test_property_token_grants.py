"""Property-based tests for token grant determinism (Task 2.2 - Property 4).

Verifies that _build_video_grants produces deterministic, role-correct grants
for any valid combination of participant role, user_id, and room_name.
"""

import pytest
from hypothesis import given, strategies as st

from livekit import api

from app.core.exceptions import InvalidRoleError
from app.services.livekit_adapter import _build_video_grants


# --- Strategies ---

valid_roles = st.sampled_from(["interviewer", "interviewee", "observer"])
user_ids = st.integers(min_value=1, max_value=10000)
room_names = st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P")))


# --- Property Tests ---


@given(user_id=user_ids, room_name=room_names)
def test_interviewer_grants_are_deterministic(user_id: int, room_name: str):
    """Interviewers always get full publish + subscribe + data permissions."""
    grants = _build_video_grants(room_name, "interviewer")

    assert grants.can_publish is True
    assert grants.can_subscribe is True
    assert grants.can_publish_data is True
    assert grants.room == room_name
    assert grants.room_join is True


@given(user_id=user_ids, room_name=room_names)
def test_interviewee_grants_are_deterministic(user_id: int, room_name: str):
    """Interviewees always get full publish + subscribe + data permissions."""
    grants = _build_video_grants(room_name, "interviewee")

    assert grants.can_publish is True
    assert grants.can_subscribe is True
    assert grants.can_publish_data is True
    assert grants.room == room_name
    assert grants.room_join is True


@given(user_id=user_ids, room_name=room_names)
def test_observer_grants_are_deterministic(user_id: int, room_name: str):
    """Observers always get subscribe-only permissions (no publish, no data)."""
    grants = _build_video_grants(room_name, "observer")

    assert grants.can_publish is False
    assert grants.can_subscribe is True
    assert grants.can_publish_data is False
    assert grants.room == room_name
    assert grants.room_join is True


@given(role=valid_roles, user_id=user_ids, room_name=room_names)
def test_grants_room_always_matches_input(role: str, user_id: int, room_name: str):
    """The token room field always equals the session room_name."""
    grants = _build_video_grants(room_name, role)
    assert grants.room == room_name


@given(role=valid_roles, user_id=user_ids, room_name=room_names)
def test_grants_are_idempotent(role: str, user_id: int, room_name: str):
    """Calling _build_video_grants twice with the same inputs yields identical results."""
    grants_a = _build_video_grants(room_name, role)
    grants_b = _build_video_grants(room_name, role)

    assert grants_a.can_publish == grants_b.can_publish
    assert grants_a.can_subscribe == grants_b.can_subscribe
    assert grants_a.can_publish_data == grants_b.can_publish_data
    assert grants_a.room == grants_b.room
    assert grants_a.room_join == grants_b.room_join


@given(
    role=valid_roles,
    user_id=user_ids,
    room_name=room_names,
)
def test_role_permission_matrix(role: str, user_id: int, room_name: str):
    """Comprehensive check: role determines exact permission set."""
    grants = _build_video_grants(room_name, role)

    if role in ("interviewer", "interviewee"):
        assert grants.can_publish is True
        assert grants.can_subscribe is True
        assert grants.can_publish_data is True
    else:
        # observer
        assert grants.can_publish is False
        assert grants.can_subscribe is True
        assert grants.can_publish_data is False


# --- Invalid Role Tests ---

invalid_roles = st.text(min_size=1, max_size=50).filter(
    lambda r: r not in ("interviewer", "interviewee", "observer")
)


@given(role=invalid_roles)
def test_invalid_role_raises_error(role: str):
    """Any role not in the valid set raises InvalidRoleError."""
    with pytest.raises(InvalidRoleError) as exc_info:
        _build_video_grants("any-room", role)
    assert exc_info.value.role == role


def test_empty_string_role_raises_error():
    """Empty string is not a valid role."""
    with pytest.raises(InvalidRoleError):
        _build_video_grants("room-1", "")


def test_none_role_raises_error():
    """None is not a valid role (not in the set)."""
    with pytest.raises((InvalidRoleError, TypeError)):
        _build_video_grants("room-1", None)
