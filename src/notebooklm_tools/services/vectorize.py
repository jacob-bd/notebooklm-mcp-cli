"""Cloudflare Vectorize service — semantic vector search over source content.

Pipeline:
  source content → chunk → embed (CF Workers AI) → upsert (CF Vectorize)
  query → embed → vector search → relevant chunks → Claude API answer

Required env vars:
  CLOUDFLARE_API_TOKEN   — CF API token with Vectorize + Workers AI permissions
  CLOUDFLARE_ACCOUNT_ID  — CF account ID
  VECTORIZE_INDEX_NAME   — Vectorize index name (default: "notebooklm-sources")
  CF_AI_MODEL            — Embedding model (default: "@cf/baai/bge-base-en-v1.5")
"""

from __future__ import annotations

import os
import re
import time
from typing import TypedDict, Optional, Any
import httpx


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _cf_config() -> dict[str, str]:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    index_name = os.environ.get("VECTORIZE_INDEX_NAME", "notebooklm-sources")
    ai_model = os.environ.get("CF_AI_MODEL", "@cf/baai/bge-base-en-v1.5")
    if not token or not account_id:
        raise ValueError(
            "CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID are required.\n"
            "Set them as environment variables."
        )
    return {
        "token": token,
        "account_id": account_id,
        "index_name": index_name,
        "ai_model": ai_model,
    }


def _cf_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 512     # approximate chars per chunk
_CHUNK_OVERLAP = 64   # overlap between chunks


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if not text:
        return []
    # Split on sentence boundaries first
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of current chunk
            words = current.split()
            overlap_text = " ".join(words[-overlap // 5:]) if len(words) > overlap // 5 else ""
            current = overlap_text + " " + sentence
        else:
            current = current + " " + sentence if current else sentence
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# Embeddings via Cloudflare Workers AI
# ---------------------------------------------------------------------------

def embed_texts(texts: list[str], config: Optional[dict] = None) -> list[list[float]]:
    """Generate embeddings using Cloudflare Workers AI REST API."""
    cfg = config or _cf_config()
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{cfg['account_id']}"
        f"/ai/run/{cfg['ai_model']}"
    )
    headers = _cf_headers(cfg["token"])

    # CF AI accepts up to 100 texts per request
    all_embeddings = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        resp = httpx.post(url, headers=headers, json={"text": batch}, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"CF AI API error: {data.get('errors', data)}")
        embeddings = data["result"]["data"]
        all_embeddings.extend(embeddings)

    return all_embeddings


# ---------------------------------------------------------------------------
# Vectorize API
# ---------------------------------------------------------------------------

def _vectorize_url(account_id: str, index_name: str, path: str = "") -> str:
    base = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/vectorize/v2/indexes/{index_name}"
    return base + path


def upsert_vectors(
    vectors: list[dict],  # [{"id": str, "values": list[float], "metadata": dict}]
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """Upsert vectors to Cloudflare Vectorize index."""
    cfg = config or _cf_config()
    url = _vectorize_url(cfg["account_id"], cfg["index_name"], "/upsert")
    headers = _cf_headers(cfg["token"])

    # Vectorize accepts NDJSON format
    ndjson_lines = []
    for v in vectors:
        import json
        ndjson_lines.append(json.dumps({"id": v["id"], "values": v["values"], "metadata": v.get("metadata", {})}))
    body = "\n".join(ndjson_lines)

    resp = httpx.post(
        url,
        headers={**headers, "Content-Type": "application/x-ndjson"},
        content=body.encode(),
        timeout=120.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Vectorize upsert error: {data.get('errors', data)}")
    return data.get("result", {})


def query_vectors(
    query_embedding: list[float],
    top_k: int = 10,
    filter_metadata: Optional[dict] = None,
    return_metadata: bool = True,
    config: Optional[dict] = None,
) -> list[dict]:
    """Query Vectorize index for nearest neighbors."""
    cfg = config or _cf_config()
    url = _vectorize_url(cfg["account_id"], cfg["index_name"], "/query")
    headers = _cf_headers(cfg["token"])

    payload: dict[str, Any] = {
        "vector": query_embedding,
        "topK": top_k,
        "returnMetadata": "all" if return_metadata else "none",
        "returnValues": False,
    }
    if filter_metadata:
        payload["filter"] = filter_metadata

    resp = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Vectorize query error: {data.get('errors', data)}")
    return data.get("result", {}).get("matches", [])


def delete_vectors_by_prefix(notebook_id: str, config: Optional[dict] = None) -> dict[str, Any]:
    """Delete all vectors for a notebook (by notebook_id metadata filter — note: Vectorize
    doesn't support delete-by-filter directly; we log the operation for now)."""
    # Vectorize v2 supports delete by IDs only.
    # A real implementation would track vector IDs per source in a local store.
    # For now, this is a no-op placeholder.
    return {"message": f"Vector deletion by notebook_id={notebook_id} requires tracking vector IDs."}


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class IndexSourceResult(TypedDict):
    source_id: str
    source_title: str
    notebook_id: str
    chunks_indexed: int
    vectors_upserted: int


class VectorSearchResult(TypedDict):
    query: str
    matches: list[dict]
    match_count: int
    answer: Optional[str]


# ---------------------------------------------------------------------------
# High-level pipeline functions
# ---------------------------------------------------------------------------

def index_source(
    client,
    source_id: str,
    notebook_id: str,
    config: Optional[dict] = None,
) -> IndexSourceResult:
    """Extract source content, chunk it, embed, and upsert to Vectorize.

    Uses cached source content (SQLite cache) to avoid repeat API calls.
    """
    from .sources import get_source_content

    cfg = config or _cf_config()

    # 1. Get source content (cached)
    result = get_source_content(client, source_id)
    content = result.get("content", "")
    title = result.get("title", source_id)

    if not content:
        return {
            "source_id": source_id,
            "source_title": title,
            "notebook_id": notebook_id,
            "chunks_indexed": 0,
            "vectors_upserted": 0,
        }

    # 2. Chunk
    chunks = chunk_text(content)
    if not chunks:
        return {
            "source_id": source_id,
            "source_title": title,
            "notebook_id": notebook_id,
            "chunks_indexed": 0,
            "vectors_upserted": 0,
        }

    # 3. Embed
    embeddings = embed_texts(chunks, config=cfg)

    # 4. Build vector objects
    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vec_id = f"{source_id[:16]}_{i:04d}"
        vectors.append({
            "id": vec_id,
            "values": embedding,
            "metadata": {
                "source_id": source_id,
                "source_title": title[:200],
                "notebook_id": notebook_id,
                "chunk_index": i,
                "chunk_text": chunk[:500],  # store preview in metadata
            },
        })

    # 5. Upsert to Vectorize (in batches of 500)
    batch_size = 500
    total_upserted = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        upsert_vectors(batch, config=cfg)
        total_upserted += len(batch)

    return {
        "source_id": source_id,
        "source_title": title,
        "notebook_id": notebook_id,
        "chunks_indexed": len(chunks),
        "vectors_upserted": total_upserted,
    }


def index_notebook(
    client,
    notebook_id: str,
    max_workers: int = 3,
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """Index all sources in a notebook to Vectorize.

    Processes sources in parallel. Uses cached content where available.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cfg = config or _cf_config()
    source_ids = client._get_cached_source_ids(notebook_id)

    results = []
    errors = []

    def index_one(sid: str) -> dict:
        try:
            r = index_source(client, sid, notebook_id, config=cfg)
            return {**r, "success": True}
        except Exception as e:
            return {"source_id": sid, "error": str(e), "success": False}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(index_one, sid): sid for sid in source_ids}
        for future in as_completed(futures):
            r = future.result()
            if r.get("success"):
                results.append(r)
            else:
                errors.append(r)

    return {
        "notebook_id": notebook_id,
        "sources_indexed": len(results),
        "sources_failed": len(errors),
        "total_chunks": sum(r.get("chunks_indexed", 0) for r in results),
        "total_vectors": sum(r.get("vectors_upserted", 0) for r in results),
        "results": results,
        "errors": errors,
    }


def vector_search(
    query: str,
    top_k: int = 10,
    notebook_id: Optional[str] = None,
    answer_with_claude: bool = False,
    config: Optional[dict] = None,
) -> VectorSearchResult:
    """Semantic vector search over indexed source content.

    Optionally answer the query using Claude API with the retrieved chunks as context.

    Args:
        query: Natural language search query
        top_k: Number of matching chunks to return
        notebook_id: Filter results to a specific notebook (optional)
        answer_with_claude: Use Claude API to answer the query using retrieved chunks
        config: Optional Cloudflare config dict
    """
    cfg = config or _cf_config()

    # 1. Embed the query
    query_embeddings = embed_texts([query], config=cfg)
    query_vec = query_embeddings[0]

    # 2. Optional metadata filter by notebook_id
    filter_meta = None
    if notebook_id:
        filter_meta = {"notebook_id": {"$eq": notebook_id}}

    # 3. Search Vectorize
    matches = query_vectors(
        query_vec,
        top_k=top_k,
        filter_metadata=filter_meta,
        return_metadata=True,
        config=cfg,
    )

    # 4. Optionally answer with Claude
    answer = None
    if answer_with_claude and matches:
        try:
            import os, anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                context_chunks = []
                for m in matches:
                    meta = m.get("metadata", {})
                    chunk_text = meta.get("chunk_text", "")
                    src_title = meta.get("source_title", "Unknown")
                    context_chunks.append(f"SOURCE: {src_title}\n{chunk_text}")

                context = "\n\n---\n\n".join(context_chunks)
                client_ai = anthropic.Anthropic(api_key=api_key)
                resp = client_ai.messages.create(
                    model=os.environ.get("NOTEBOOKLM_AGENT_MODEL", "claude-haiku-4-5-20251001"),
                    max_tokens=2048,
                    system="Answer the question using ONLY the provided source excerpts. Cite sources by title.",
                    messages=[{"role": "user", "content": f"<sources>\n{context}\n</sources>\n\nQuestion: {query}"}],
                )
                answer = resp.content[0].text if resp.content else None
        except Exception:
            pass

    return {
        "query": query,
        "matches": [
            {
                "score": m.get("score", 0),
                "source_id": m.get("metadata", {}).get("source_id", ""),
                "source_title": m.get("metadata", {}).get("source_title", ""),
                "notebook_id": m.get("metadata", {}).get("notebook_id", ""),
                "chunk_index": m.get("metadata", {}).get("chunk_index", 0),
                "chunk_text": m.get("metadata", {}).get("chunk_text", ""),
            }
            for m in matches
        ],
        "match_count": len(matches),
        "answer": answer,
    }
