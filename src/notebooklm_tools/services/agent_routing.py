"""Agent routing — score notebooks by keyword relevance and route queries."""

from __future__ import annotations

from typing import TypedDict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .agent_registry import get_registry, AgentEntry


class RoutingScore(TypedDict):
    notebook_id: str
    title: str
    domain: str
    score: float
    source_count: int


class AgentRoutingResult(TypedDict):
    answer: str
    notebook_id: str
    notebook_title: str
    score: float
    case_file_hit: bool


class MultiAgentResult(TypedDict):
    query: str
    results: list[dict]
    synthesis: Optional[str]
    notebooks_queried: int


def _score_notebooks(query: str, agents: list[AgentEntry]) -> list[RoutingScore]:
    """Score notebooks by how many query words appear in the notebook title."""
    query_words = set(query.lower().split())
    scored = []
    for agent in agents:
        title_words = set(agent.get("title", "").lower().split())
        score = len(query_words & title_words)
        scored.append({
            "notebook_id": agent["notebook_id"],
            "title": agent["title"],
            "domain": agent.get("domain", "general"),
            "score": float(score),
            "source_count": agent.get("source_count", 0),
        })
    scored.sort(key=lambda x: -x["score"])
    return scored


def notebook_agent_query(
    client,
    query: str,
    top_k: int = 1,
    domain_filter: Optional[str] = None,
) -> AgentRoutingResult:
    """Route query to the best-matching notebook and return the answer.

    1. Check case files first (instant local lookup)
    2. Load registry, score notebooks by keyword overlap
    3. Query the top notebook via NotebookLM chat
    4. Write answer back as a case file
    """
    # Step 1: Check case files first
    try:
        from .case_files import case_file_search, case_file_save
        cf_result = case_file_search(query)
        if cf_result["match_count"] > 0:
            best = cf_result["matches"][0]
            from .case_files import case_file_get
            cf = case_file_get(key=best["key"])
            return {
                "answer": cf["content"][:3000],
                "notebook_id": "",
                "notebook_title": f"[Case File] {best['key']}",
                "score": 999.0,
                "case_file_hit": True,
            }
    except Exception:
        pass

    # Step 2: Load registry
    registry = get_registry(filter_domain=domain_filter)
    agents = registry.get("agents", [])
    if not agents:
        raise ValueError("Agent registry is empty. Run agent_registry_build() first.")

    scored = _score_notebooks(query, agents)
    if not scored:
        raise ValueError("No notebooks matched the query.")

    top = scored[0]
    notebook_id = top["notebook_id"]

    # Find the matching agent entry to get per-notebook instructions
    agent_entry = next((a for a in agents if a["notebook_id"] == notebook_id), {})
    instructions = agent_entry.get("instructions", "")

    # Step 3: Query the notebook — prepend instructions if present
    from .chat import query as chat_query
    effective_query = f"{instructions}\n\n---\n\n{query}" if instructions else query
    query_result = chat_query(client, notebook_id, effective_query)
    answer = query_result.get("answer", "") if isinstance(query_result, dict) else str(query_result)

    # Step 4: Write-back as case file
    try:
        from .case_files import case_file_save
        import re
        safe_q = re.sub(r"[^\w]", "_", query[:50])
        case_file_save("research", f"query_{safe_q}.md", f"# Query: {query}\n\n{answer}")
    except Exception:
        pass

    # Step 5: Self-update — append findings to the notebook note (GDoc data layer)
    if agent_entry.get("gdoc_id"):
        try:
            from .gdoc_sync import agent_append_findings
            agent_append_findings(client, notebook_id, query, answer)
        except Exception:
            pass

    return {
        "answer": answer,
        "notebook_id": notebook_id,
        "notebook_title": top["title"],
        "score": top["score"],
        "case_file_hit": False,
    }


def notebook_agent_multi_query(
    client,
    query: str,
    top_k: int = 3,
    aggregate: bool = True,
    domain_filter: Optional[str] = None,
) -> MultiAgentResult:
    """Fan-out query to top_k matching notebooks in parallel."""
    registry = get_registry(filter_domain=domain_filter)
    agents = registry.get("agents", [])
    if not agents:
        raise ValueError("Agent registry is empty. Run agent_registry_build() first.")

    scored = _score_notebooks(query, agents)
    top_notebooks = scored[:top_k]

    results = []

    def query_one(nb_info: dict) -> dict:
        from .chat import query as chat_query
        try:
            query_result = chat_query(client, nb_info["notebook_id"], query)
            answer = query_result.get("answer", "") if isinstance(query_result, dict) else str(query_result)
            return {
                "notebook_id": nb_info["notebook_id"],
                "notebook_title": nb_info["title"],
                "score": nb_info["score"],
                "answer": answer,
                "error": None,
            }
        except Exception as e:
            return {
                "notebook_id": nb_info["notebook_id"],
                "notebook_title": nb_info["title"],
                "score": nb_info["score"],
                "answer": None,
                "error": str(e),
            }

    with ThreadPoolExecutor(max_workers=min(top_k, 5)) as executor:
        futures = {executor.submit(query_one, nb): nb for nb in top_notebooks}
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: -x["score"])

    synthesis = None
    if aggregate and len(results) > 1:
        valid_answers = [r["answer"] for r in results if r["answer"]]
        if valid_answers:
            synthesis = "\n\n---\n\n".join(
                f"**From {results[i]['notebook_title']}:**\n{ans}"
                for i, ans in enumerate(valid_answers)
            )

    return {
        "query": query,
        "results": results,
        "synthesis": synthesis,
        "notebooks_queried": len(results),
    }
