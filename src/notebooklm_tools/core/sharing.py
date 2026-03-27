"""SharingMixin - Notebook sharing and collaboration operations.

This mixin provides sharing-related operations:
- get_share_status: Get current collaborators and public access
- set_public_access: Toggle public link access
- add_collaborator: Add a collaborator by email
- add_collaborators_bulk: Add multiple collaborators in a single API call
"""

from . import constants
from .base import BaseClient
from .data_types import Collaborator, ShareStatus


class SharingMixin(BaseClient):
    """Mixin for notebook sharing and collaboration operations.

    This class inherits from BaseClient and provides all sharing-related
    operations. It is designed to be composed with other mixins via
    multiple inheritance in the final NotebookLMClient class.
    """

    def get_share_status(self, notebook_id: str) -> ShareStatus:
        """Get current sharing settings and collaborators.

        Args:
            notebook_id: The notebook UUID

        Returns:
            ShareStatus with collaborators list, public access status, and link
        """
        params = [notebook_id, [2]]
        result = self._call_rpc(self.RPC_GET_SHARE_STATUS, params)

        # Parse collaborators from response
        # Response structure: [[collaborator_data...], access_info, ...]
        collaborators: list[Collaborator] = []
        is_public = False
        public_link = None

        if result and isinstance(result, list):
            # Parse collaborators (usually at position 0 or 1)
            for item in result:
                if isinstance(item, list):
                    for entry in item:
                        if isinstance(entry, list) and len(entry) >= 2:
                            # Collaborator format: [email, role_code, [], [name, avatar_url]]
                            email = entry[0] if entry[0] else None
                            if email and isinstance(email, str) and "@" in email:
                                role_code = (
                                    entry[1] if len(entry) > 1 and isinstance(entry[1], int) else 3
                                )
                                role = constants.SHARE_ROLES.get_name(role_code)
                                # Name is in entry[3][0] if present
                                display_name = None
                                if (
                                    len(entry) > 3
                                    and isinstance(entry[3], list)
                                    and len(entry[3]) > 0
                                ):
                                    display_name = entry[3][0]
                                # Pending invites may have additional flag
                                is_pending = len(entry) > 4 and entry[4] is True
                                collaborators.append(
                                    Collaborator(
                                        email=email,
                                        role=role,
                                        is_pending=is_pending,
                                        display_name=str(display_name) if display_name else None,
                                    )
                                )

            # Check for public access flag
            # Usually indicated by access level code in the response
            # Position varies; look for [1] pattern indicating public
            for item in result:
                if isinstance(item, list) and len(item) >= 1:  # noqa: SIM102
                    if item[0] == 1:  # Public access indicator
                        is_public = True
                        break

        # Construct public link if public
        if is_public:
            public_link = f"{self._get_base_url()}/notebook/{notebook_id}"

        access_level = "public" if is_public else "restricted"

        return ShareStatus(
            is_public=is_public,
            access_level=access_level,
            collaborators=collaborators,
            public_link=public_link,
        )

    def set_public_access(self, notebook_id: str, is_public: bool = True) -> str | None:
        """Toggle public link access for a notebook.

        Args:
            notebook_id: The notebook UUID
            is_public: True to enable public link, False to disable

        Returns:
            The public URL if enabled, None if disabled
        """
        # Payload: [[[notebook_id, null, [access_level], [notify, ""]]], 1, null, [2]]
        # access_level: 0 = restricted, 1 = public
        access_code = self.SHARE_ACCESS_PUBLIC if is_public else self.SHARE_ACCESS_RESTRICTED

        params = [[[notebook_id, None, [access_code], [0, ""]]], 1, None, [2]]

        self._call_rpc(self.RPC_SHARE_NOTEBOOK, params)

        if is_public:
            return f"{self._get_base_url()}/notebook/{notebook_id}"
        return None

    def add_collaborator(
        self,
        notebook_id: str,
        email: str,
        role: str = "viewer",
        notify: bool = True,
        message: str = "",
    ) -> bool:
        """Add a collaborator to a notebook by email.

        Args:
            notebook_id: The notebook UUID
            email: Email address of the collaborator
            role: "viewer" or "editor" (default: viewer)
            notify: Send email notification (default: True)
            message: Optional welcome message

        Returns:
            True if successful
        """
        # Validate role
        role_code = constants.SHARE_ROLES.get_code(role)
        if role_code == constants.SHARE_ROLE_OWNER:
            raise ValueError("Cannot add collaborator as owner")

        # Payload: [[[notebook_id, [[email, null, role_code]], null, [notify_flag, message]]], 1, null, [2]]
        notify_flag = 0 if notify else 1  # 0 = notify, 1 = don't notify

        params = [
            [[notebook_id, [[email, None, role_code]], None, [notify_flag, message]]],
            1,
            None,
            [2],
        ]

        result = self._call_rpc(self.RPC_SHARE_NOTEBOOK, params)

        # Success if result is not None (no error thrown)
        return result is not None

    def add_collaborators_bulk(
        self,
        notebook_id: str,
        recipients: list[dict],
        notify: bool = True,
        message: str = "",
    ) -> bool:
        """Add multiple collaborators to a notebook in a single API call.

        Args:
            notebook_id: The notebook UUID
            recipients: List of dicts, each with 'email' (str) and 'role' (str).
                        Role must be 'viewer' or 'editor'.
            notify: Send email notification (default: True)
            message: Optional welcome message

        Returns:
            True if successful

        Raises:
            ValueError: If any role is invalid or recipients list is empty
        """
        if not recipients:
            raise ValueError("Recipients list cannot be empty")

        # Build the multi-email array: [[email1, None, role_code1], [email2, None, role_code2], ...]
        email_items = []
        for recipient in recipients:
            email = recipient["email"]
            role = recipient.get("role", "viewer")
            role_code = constants.SHARE_ROLES.get_code(role)
            if role_code == constants.SHARE_ROLE_OWNER:
                raise ValueError(f"Cannot add collaborator '{email}' as owner")
            email_items.append([email, None, role_code])

        notify_flag = 0 if notify else 1  # 0 = notify, 1 = don't notify

        params = [[[notebook_id, email_items, None, [notify_flag, message]]], 1, None, [2]]

        result = self._call_rpc(self.RPC_SHARE_NOTEBOOK, params)

        return result is not None
