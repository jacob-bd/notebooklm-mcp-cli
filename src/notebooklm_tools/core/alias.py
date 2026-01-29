"""Alias management for NotebookLM CLI."""

import json
from pathlib import Path
from typing import Any

from notebooklm_tools.utils.config import get_config_dir


class AliasEntry:
    """Represents an alias with its value and type."""
    
    def __init__(self, value: str, alias_type: str = "unknown") -> None:
        self.value = value
        self.type = alias_type
    
    def to_dict(self) -> dict[str, str]:
        return {"value": self.value, "type": self.type}
    
    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> "AliasEntry":
        """Create from dict or legacy string format."""
        if isinstance(data, str):
            # Legacy format: just the value
            return cls(value=data, alias_type="unknown")
        return cls(value=data.get("value", ""), alias_type=data.get("type", "unknown"))


class AliasManager:
    """Manages user-defined aliases for IDs."""

    def __init__(self) -> None:
        self.config_dir = get_config_dir()
        self.aliases_file = self.config_dir / "aliases.json"
        self._aliases: dict[str, AliasEntry] = {}
        self._load()

    def _load(self) -> None:
        """Load aliases from disk."""
        if not self.aliases_file.exists():
            return
        
        try:
            content = self.aliases_file.read_text()
            if content:
                raw_data = json.loads(content)
                # Convert to AliasEntry objects (handles legacy format)
                self._aliases = {
                    name: AliasEntry.from_dict(data) 
                    for name, data in raw_data.items()
                }
        except Exception:
            # On error, start with empty map
            self._aliases = {}

    def _save(self) -> None:
        """Save aliases to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = {name: entry.to_dict() for name, entry in self._aliases.items()}
        self.aliases_file.write_text(json.dumps(data, indent=2))

    def set_alias(self, name: str, value: str, alias_type: str = "unknown") -> None:
        """Set an alias with optional type."""
        self._aliases[name] = AliasEntry(value=value, alias_type=alias_type)
        self._save()

    def get_alias(self, name: str) -> str | None:
        """Get an alias value."""
        entry = self._aliases.get(name)
        return entry.value if entry else None
    
    def get_entry(self, name: str) -> AliasEntry | None:
        """Get the full alias entry including type."""
        return self._aliases.get(name)

    def delete_alias(self, name: str) -> bool:
        """Delete an alias. Returns True if deleted."""
        if name in self._aliases:
            del self._aliases[name]
            self._save()
            return True
        return False

    def list_aliases(self) -> dict[str, AliasEntry]:
        """List all aliases with their types."""
        return self._aliases.copy()

    def resolve(self, id_or_alias: str) -> str:
        """
        Resolve an ID or alias to its value.
        If the input matches a known alias, return the aliased value.
        Otherwise return the input as-is.
        """
        entry = self._aliases.get(id_or_alias)
        return entry.value if entry else id_or_alias


# Global instance
_alias_manager: AliasManager | None = None


def get_alias_manager() -> AliasManager:
    """Get the global alias manager instance."""
    global _alias_manager
    if _alias_manager is None:
        _alias_manager = AliasManager()
    return _alias_manager


def detect_id_type(value: str, profile: str | None = None) -> str:
    """
    Detect the type of an ID by trying API calls.
    
    Returns: "notebook", "source", or "unknown"
    """
    from notebooklm_tools.cli.utils import get_client
    from notebooklm_tools.core.exceptions import NLMError
    
    try:
        with get_client(profile) as client:
            # Try as notebook ID first (most common)
            try:
                notebook = client.get_notebook(value)
                if notebook:
                    return "notebook"
            except NLMError:
                pass
            
            # Try as source ID
            try:
                # Sources need a notebook context, but we can try to get source content
                content = client.get_source_content(value)
                if content:
                    return "source"
            except NLMError:
                pass
            
    except NLMError:
        pass
    
    return "unknown"
