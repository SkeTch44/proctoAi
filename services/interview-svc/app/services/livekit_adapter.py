"""LiveKit adapter — abstraction over LiveKit Server SDK for room and token management."""

import asyncio
import logging
from datetime import timedelta

from livekit import api

from app.core.config import get_settings
from app.core.exceptions import InvalidRoleError, ServiceUnavailableError

logger = logging.getLogger(__name__)

# Maximum token TTL: 24 hours
_MAX_TOKEN_TTL = timedelta(hours=24)

# Timeout for all LiveKit API calls (seconds)
_API_TIMEOUT = 5

# Retry configuration for delete_room
_DELETE_RETRY_ATTEMPTS = 3
_DELETE_RETRY_INTERVAL = 5  # seconds

# Valid participant roles
_VALID_ROLES = {"interviewer", "interviewee", "observer"}


def _build_video_grants(room_name: str, role: str) -> api.VideoGrants:
    """Build VideoGrants based on participant role.

    Args:
        room_name: The LiveKit room name to scope the token to.
        role: One of 'interviewer', 'interviewee', or 'observer'.

    Returns:
        VideoGrants with appropriate permissions.

    Raises:
        InvalidRoleError: If the role is not valid.
    """
    if role not in _VALID_ROLES:
        raise InvalidRoleError(role)

    if role in ("interviewer", "interviewee"):
        return api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )
    else:
        # observer
        return api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=False,
            can_subscribe=True,
            can_publish_data=False,
        )


class LiveKitAdapter:
    """Manages LiveKit room lifecycle and token generation.

    All API calls enforce a 5-second timeout and raise ServiceUnavailableError
    on timeout or connection failure.
    """

    def __init__(self):
        settings = get_settings()
        self.url = settings.LIVEKIT_URL
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET

    def _get_api(self) -> api.LiveKitAPI:
        """Create a LiveKitAPI client instance."""
        return api.LiveKitAPI(
            url=self.url,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

    async def create_room(
        self,
        room_name: str,
        max_participants: int = 6,
        empty_timeout: int = 300,
    ) -> dict:
        """Create a LiveKit room.

        Args:
            room_name: Unique name for the room.
            max_participants: Maximum number of participants allowed.
            empty_timeout: Seconds before an empty room is automatically closed.

        Returns:
            Room info dict with room details.

        Raises:
            ServiceUnavailableError: If the LiveKit server is unreachable or times out.
        """
        lk = self._get_api()
        try:
            room_info = await asyncio.wait_for(
                lk.room.create_room(
                    api.CreateRoomRequest(
                        name=room_name,
                        max_participants=max_participants,
                        empty_timeout=empty_timeout,
                    )
                ),
                timeout=_API_TIMEOUT,
            )
            return {
                "name": room_info.name,
                "sid": room_info.sid,
                "max_participants": room_info.max_participants,
                "empty_timeout": room_info.empty_timeout,
            }
        except asyncio.TimeoutError as exc:
            logger.error("LiveKit create_room timed out for room '%s'", room_name)
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        except Exception as exc:
            logger.error("LiveKit create_room failed for room '%s': %s", room_name, exc)
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        finally:
            await lk.aclose()

    def generate_token(
        self,
        room_name: str,
        identity: str,
        name: str,
        grants: dict | None = None,
        role: str | None = None,
    ) -> str:
        """Generate a scoped LiveKit access token.

        The token is scoped to the specific room_name, with identity set to the
        user_id string, and a TTL of 24 hours maximum.

        Args:
            room_name: The LiveKit room name to scope the token to.
            identity: The participant identity (str(user_id)).
            name: The participant display name.
            grants: Optional dict with grant overrides. If not provided, role must be set.
            role: Participant role ('interviewer', 'interviewee', 'observer').
                  Used to determine grants if grants dict is not provided.

        Returns:
            JWT access token string.

        Raises:
            InvalidRoleError: If the role is invalid.
            ServiceUnavailableError: If token generation fails.
        """
        try:
            # Build video grants from role or provided grants dict
            if grants is not None and isinstance(grants, api.VideoGrants):
                video_grants = grants
            elif role is not None:
                video_grants = _build_video_grants(room_name, role)
            elif grants is not None and isinstance(grants, dict):
                # Build from dict — validate role if present
                effective_role = grants.get("role")
                if effective_role:
                    video_grants = _build_video_grants(room_name, effective_role)
                else:
                    video_grants = api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=grants.get("can_publish", False),
                        can_subscribe=grants.get("can_subscribe", True),
                        can_publish_data=grants.get("can_publish_data", False),
                    )
            else:
                raise InvalidRoleError("unknown")

            token = (
                api.AccessToken(api_key=self.api_key, api_secret=self.api_secret)
                .with_identity(identity)
                .with_name(name)
                .with_grants(video_grants)
                .with_ttl(_MAX_TOKEN_TTL)
                .to_jwt()
            )
            return token
        except InvalidRoleError:
            raise
        except Exception as exc:
            logger.error("LiveKit token generation failed: %s", exc)
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc

    async def delete_room(self, room_name: str) -> None:
        """Delete a LiveKit room with retry logic.

        Retries up to 3 times with 5-second intervals between attempts.

        Args:
            room_name: The name of the room to delete.

        Raises:
            ServiceUnavailableError: If all retry attempts fail.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _DELETE_RETRY_ATTEMPTS + 1):
            lk = self._get_api()
            try:
                await asyncio.wait_for(
                    lk.room.delete_room(
                        api.DeleteRoomRequest(room=room_name)
                    ),
                    timeout=_API_TIMEOUT,
                )
                logger.info("LiveKit room '%s' deleted (attempt %d)", room_name, attempt)
                return
            except asyncio.TimeoutError as exc:
                last_exc = exc
                logger.warning(
                    "LiveKit delete_room timed out for room '%s' (attempt %d/%d)",
                    room_name,
                    attempt,
                    _DELETE_RETRY_ATTEMPTS,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LiveKit delete_room failed for room '%s' (attempt %d/%d): %s",
                    room_name,
                    attempt,
                    _DELETE_RETRY_ATTEMPTS,
                    exc,
                )
            finally:
                await lk.aclose()

            # Wait before retrying (skip wait after last attempt)
            if attempt < _DELETE_RETRY_ATTEMPTS:
                await asyncio.sleep(_DELETE_RETRY_INTERVAL)

        logger.error(
            "LiveKit delete_room failed after %d attempts for room '%s'",
            _DELETE_RETRY_ATTEMPTS,
            room_name,
        )
        raise ServiceUnavailableError(service="LiveKit", retry_after=5) from last_exc

    async def remove_participant(self, room_name: str, identity: str) -> None:
        """Remove a participant from a LiveKit room.

        Args:
            room_name: The room to remove the participant from.
            identity: The participant identity to remove.

        Raises:
            ServiceUnavailableError: If the LiveKit server is unreachable or times out.
        """
        lk = self._get_api()
        try:
            await asyncio.wait_for(
                lk.room.remove_participant(
                    api.RoomParticipantIdentity(room=room_name, identity=identity)
                ),
                timeout=_API_TIMEOUT,
            )
            logger.info(
                "Removed participant '%s' from room '%s'", identity, room_name
            )
        except asyncio.TimeoutError as exc:
            logger.error(
                "LiveKit remove_participant timed out for '%s' in room '%s'",
                identity,
                room_name,
            )
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        except Exception as exc:
            logger.error(
                "LiveKit remove_participant failed for '%s' in room '%s': %s",
                identity,
                room_name,
                exc,
            )
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        finally:
            await lk.aclose()

    async def send_data(self, room_name: str, data: str | bytes) -> None:
        """Send data to all participants in a LiveKit room via data channel.

        Args:
            room_name: The room to send data to.
            data: The data payload (string or bytes) to broadcast.

        Raises:
            ServiceUnavailableError: If the LiveKit server is unreachable or times out.
        """
        lk = self._get_api()
        try:
            payload = data.encode("utf-8") if isinstance(data, str) else data
            await asyncio.wait_for(
                lk.room.send_data(
                    api.SendDataRequest(
                        room=room_name,
                        data=payload,
                        reliable=True,
                    )
                ),
                timeout=_API_TIMEOUT,
            )
            logger.info("Sent data to room '%s' (%d bytes)", room_name, len(payload))
        except asyncio.TimeoutError as exc:
            logger.error("LiveKit send_data timed out for room '%s'", room_name)
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        except Exception as exc:
            logger.error("LiveKit send_data failed for room '%s': %s", room_name, exc)
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        finally:
            await lk.aclose()

    async def list_participants(self, room_name: str) -> list[dict]:
        """List participants in a LiveKit room.

        Args:
            room_name: The room to query.

        Returns:
            List of participant info dicts with identity, name, and state.

        Raises:
            ServiceUnavailableError: If the LiveKit server is unreachable or times out.
        """
        lk = self._get_api()
        try:
            response = await asyncio.wait_for(
                lk.room.list_participants(
                    api.ListParticipantsRequest(room=room_name)
                ),
                timeout=_API_TIMEOUT,
            )
            return [
                {
                    "identity": p.identity,
                    "name": p.name,
                    "sid": p.sid,
                    "state": p.state,
                }
                for p in response.participants
            ]
        except asyncio.TimeoutError as exc:
            logger.error(
                "LiveKit list_participants timed out for room '%s'", room_name
            )
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        except Exception as exc:
            logger.error(
                "LiveKit list_participants failed for room '%s': %s", room_name, exc
            )
            raise ServiceUnavailableError(service="LiveKit", retry_after=5) from exc
        finally:
            await lk.aclose()
