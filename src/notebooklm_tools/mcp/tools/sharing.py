"""Sharing tools - Notebook sharing and collaboration."""

from ...services import ServiceError
from ...services import sharing as sharing_service
from ._utils import ResultDict, error_result, get_client, logged_tool


@logged_tool()
def notebook_share_status(notebook_id: str) -> ResultDict:
    """Get current sharing settings and collaborators.

    Args:
        notebook_id: Notebook UUID

    Returns: is_public, access_level, collaborators list, and public_link if public
    """
    try:
        client = get_client()
        result = sharing_service.get_share_status(client, notebook_id)
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def notebook_share_public(
    notebook_id: str,
    is_public: bool = True,
) -> ResultDict:
    """Enable or disable public link access.

    Args:
        notebook_id: Notebook UUID
        is_public: True to enable public link, False to disable (default: True)

    Returns: public_link if enabled, None if disabled
    """
    try:
        client = get_client()
        result = sharing_service.set_public_access(client, notebook_id, is_public)
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def notebook_share_invite(
    notebook_id: str,
    email: str,
    role: str = "viewer",
) -> ResultDict:
    """Invite a collaborator by email.

    Args:
        notebook_id: Notebook UUID
        email: Email address to invite
        role: "viewer" or "editor" (default: viewer)

    Returns: success status
    """
    try:
        client = get_client()
        result = sharing_service.invite_collaborator(client, notebook_id, email, role)
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))


@logged_tool()
def notebook_share_batch(
    notebook_id: str,
    recipients: list[dict[str, str]],
    confirm: bool = False,
) -> ResultDict:
    """Invite multiple collaborators in a single request.

    Args:
        notebook_id: Notebook UUID
        recipients: List of dicts, each with 'email' (str) and optional 'role' (str).
                    Role defaults to 'viewer'. Example: [{"email": "a@b.com", "role": "editor"}]
        confirm: Must be True after user approval

    Returns: invited_count, recipients list, and message
    """
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": f"About to invite {len(recipients)} collaborators. Set confirm=True to proceed.",
            "recipients": recipients,
        }
    try:
        client = get_client()
        result = sharing_service.invite_collaborators_bulk(client, notebook_id, recipients)
        return {"status": "success", **result}
    except ServiceError as e:
        return error_result(e.user_message, hint=e.hint)
    except Exception as e:
        return error_result(str(e))
