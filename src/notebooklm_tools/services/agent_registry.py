"""Agent registry — index of all notebooks by domain and keywords for routing."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Optional

from ..utils.config import get_storage_dir


# ---------------------------------------------------------------------------
# Domain classification
# ---------------------------------------------------------------------------

_DOMAIN_PATTERNS: list[tuple[str, list[str]]] = [
    ("foreclosure", ["foreclosure", "foreclos"]),
    ("chain of title", ["chain", "assignment", "deed", "mers", "title"]),
    ("violations", ["violation", "respa", "tila", "fdcpa", "udap"]),
    ("bankruptcy", ["bankruptcy", "chapter 7", "chapter 11", "chapter 13", "bk"]),
    ("filing", ["filing", "motion", "docket", "complaint", "petition", "pleading"]),
    ("discovery", ["discovery", "interrogatory", "deposition", "subpoena", "rfp"]),
    ("email", ["email", "correspondence", "letter", "communication"]),
    ("evidence", ["evidence", "exhibit", "smoking gun", "proof"]),
    ("timeline", ["timeline", "chronology", "chronological", "history"]),
    ("damages", ["damages", "compensation", "loss", "harm"]),
    ("constitutional", ["constitutional", "article xvi", "texas constitution", "due process"]),
    ("servicing", ["servicing", "fay", "nationstar", "ocwen", "payment", "escrow"]),
    ("perjury", ["perjury", "estoppel", "fraud", "misrepresentation", "false"]),
]

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "for", "of", "in", "on", "to", "with",
    "this", "that", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "notebook", "notebooklm", "source", "sources",
    "document", "documents", "file", "files",
}


def _classify_domain(title: str, keywords: list[str]) -> str:
    text = (title + " " + " ".join(keywords)).lower()
    for domain, patterns in _DOMAIN_PATTERNS:
        if any(p in text for p in patterns):
            return domain
    return "general"


def _extract_keywords(title: str, source_titles: Optional[list[str]] = None) -> list[str]:
    all_text = title
    if source_titles:
        all_text += " " + " ".join(source_titles[:20])
    words = re.findall(r"\b[a-zA-Z]{3,}\b", all_text.lower())
    keywords = list(dict.fromkeys(w for w in words if w not in _STOP_WORDS))
    return keywords[:30]


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class AgentEntry(TypedDict):
    notebook_id: str
    title: str
    domain: str
    keywords: list[str]
    source_count: int


class RegistryResult(TypedDict):
    agents: list[AgentEntry]
    count: int
    domains: list[str]
    built_at: str


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _registry_path() -> Path:
    return get_storage_dir() / "agent_registry.json"


def _load_raw() -> dict:
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_raw(data: dict) -> None:
    _registry_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_registry(client, force: bool = False) -> RegistryResult:
    """Build the agent registry by indexing all notebooks.

    Skips if registry already exists and force=False.
    """
    from .notebooks import list_notebooks

    existing = _load_raw()
    if existing and not force:
        return get_registry()

    notebooks_result = list_notebooks(client, max_results=500, use_cache=True)
    notebooks = notebooks_result.get("notebooks", [])

    agents: list[AgentEntry] = []
    for nb in notebooks:
        title = nb.get("title", "Untitled")
        source_count = nb.get("source_count", 0)
        keywords = _extract_keywords(title)
        domain = _classify_domain(title, keywords)
        agents.append({
            "notebook_id": nb["id"],
            "title": title,
            "domain": domain,
            "keywords": keywords,
            "source_count": source_count,
        })

    built_at = datetime.now(timezone.utc).isoformat()
    domains = sorted(set(a["domain"] for a in agents))

    data = {
        "agents": agents,
        "count": len(agents),
        "domains": domains,
        "built_at": built_at,
    }
    _save_raw(data)
    return data  # type: ignore[return-value]


def get_registry(filter_domain: Optional[str] = None) -> RegistryResult:
    """Load registry from disk. Returns empty result if not built yet."""
    data = _load_raw()
    if not data:
        return {
            "agents": [],
            "count": 0,
            "domains": [],
            "built_at": "",
        }
    agents = data.get("agents", [])
    if filter_domain:
        agents = [a for a in agents if a.get("domain") == filter_domain]
    domains = data.get("domains", sorted(set(a.get("domain", "general") for a in data.get("agents", []))))
    return {
        "agents": agents,
        "count": len(agents),
        "domains": domains,
        "built_at": data.get("built_at", ""),
    }


def update_registry_entry(
    notebook_id: str,
    domain: Optional[str] = None,
    keywords: Optional[list[str]] = None,
) -> RegistryResult:
    """Update a single registry entry's domain or keywords."""
    data = _load_raw()
    if not data:
        raise ValueError("Registry not built yet. Run build_registry() first.")

    agents = data.get("agents", [])
    for agent in agents:
        if agent["notebook_id"] == notebook_id:
            if domain is not None:
                agent["domain"] = domain
            if keywords is not None:
                agent["keywords"] = keywords
            break
    else:
        raise ValueError(f"Notebook {notebook_id} not found in registry.")

    data["agents"] = agents
    data["domains"] = sorted(set(a.get("domain", "general") for a in agents))
    _save_raw(data)
    return get_registry()
