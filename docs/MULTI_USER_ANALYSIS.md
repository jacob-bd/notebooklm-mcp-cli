# NotebookLM MCP Server: Multi-User Analysis

## Executive Summary

This document focuses on enabling **multiple users to share a single NotebookLM account** while maintaining conversation isolation. This is the recommended approach for teams sharing a NotebookLM Plus subscription through Open WebUI or similar chatbot interfaces.

**Key Goal:** Multiple users query the same notebooks, but each user has isolated conversation context.

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Solution Overview](#solution-overview)
3. [Other Approaches (Brief)](#other-approaches-brief)
4. [Shared Account Implementation](#shared-account-implementation)
5. [Open WebUI Integration](#open-webui-integration)
6. [Quick Start Guide](#quick-start-guide)

---

## The Problem

### Current Single-User Architecture

The MCP server currently uses a global singleton pattern:

```python
_client: NotebookLMClient | None = None  # Single shared client
```

| Component | Issue for Multi-User |
|-----------|---------------------|
| Conversation Cache | Shared between all users - context bleeds across |
| Rate Limits | Single account quota consumed by all users |
| Session State | One user's actions affect others |

### The User Identity Challenge

When Open WebUI connects to the MCP server, there's no built-in way to identify which user is making the request:

```
┌─────────────────────────────────────────────────────────────────┐
│                    The User Identity Problem                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐                                                    │
│  │  Alice   │──┐                                                 │
│  │(browser) │  │     ┌─────────────┐     ┌─────────────────┐    │
│  └──────────┘  │     │             │     │                 │    │
│                ├────▶│  Open WebUI │────▶│  MCP Server     │    │
│  ┌──────────┐  │     │             │     │                 │    │
│  │   Bob    │──┘     └─────────────┘     │  WHO IS THIS?   │    │
│  │(browser) │                            │  🤔              │    │
│  └──────────┘                            └─────────────────┘    │
│                                                                   │
│  Open WebUI knows the user, but MCP server doesn't!              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Solution Overview

### Shared Account with User Isolation

**Architecture:** Single NotebookLM account, with application-level user isolation for conversations.

```
┌─────────────────────────────────────────────────────────────────┐
│              Shared Account with User Isolation                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────┐                                                    │
│  │  User A  │──┐                                                 │
│  └──────────┘  │     ┌────────────────────────────────────┐     │
│                │     │  MCP Server                        │     │
│  ┌──────────┐  │     │  ┌──────────────────────────────┐  │     │
│  │  User B  │──┼────▶│  │  User Isolation Layer        │  │     │
│  └──────────┘  │     │  │  ┌────────┐ ┌────────┐       │  │     │
│                │     │  │  │User A  │ │User B  │       │  │     │
│  ┌──────────┐  │     │  │  │Context │ │Context │       │  │     │
│  │  User C  │──┘     │  │  └───┬────┘ └───┬────┘       │  │     │
│  └──────────┘        │  └──────┼──────────┼────────────┘  │     │
│                      │         │          │               │     │
│                      │         ▼          ▼               │     │
│                      │  ┌──────────────────────────────┐  │     │
│                      │  │  Single NotebookLMClient     │  │     │
│                      │  │  (Shared Google Account)     │  │     │
│                      │  └──────────────────────────────┘  │     │
│                      └────────────────────────────────────┘     │
│                                    │                             │
│                                    ▼                             │
│                      ┌────────────────────────┐                 │
│                      │  NotebookLM API        │                 │
│                      │  (Single Account)      │                 │
│                      └────────────────────────┘                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**What's Shared:**
- NotebookLM account authentication
- All notebooks and sources
- Rate limits (distributed fairly)

**What's Isolated:**
- Conversation history per user
- Query context and follow-ups
- Rate limit tracking per user

---

## Other Approaches (Brief)

For reference, there are alternative multi-user approaches. These are **not the focus** of this document:

| Approach | Description | Best For |
|----------|-------------|----------|
| **Per-User Accounts** | Each user authenticates their own NotebookLM account | Enterprise with separate subscriptions |
| **Stateless Requests** | Token passed in every request, no server state | API/microservices architecture |
| **Session-Based** | HTTP sessions with per-session client instances | Traditional web applications |

**This document focuses on Shared Account mode** - ideal for teams sharing one NotebookLM Plus subscription.

---

## Shared Account Implementation

### 1. Conversation Isolation

Each user's conversations are tracked separately using user-prefixed conversation IDs:

```python
from dataclasses import dataclass, field
import uuid

@dataclass
class UserConversationManager:
    """Manages conversation isolation for shared account mode."""
    
    # User ID -> {notebook_id -> conversation_id}
    _user_conversations: dict[str, dict[str, str]] = field(default_factory=dict)
    
    # Conversation ID -> list of turns
    _conversation_cache: dict[str, list] = field(default_factory=dict)
    
    def get_conversation_id(
        self,
        user_id: str,
        notebook_id: str,
        create_new: bool = False,
    ) -> str:
        """Get or create a user-scoped conversation ID."""
        if user_id not in self._user_conversations:
            self._user_conversations[user_id] = {}
        
        user_convs = self._user_conversations[user_id]
        
        if notebook_id not in user_convs or create_new:
            # Create new conversation with user-scoped ID
            user_convs[notebook_id] = f"{user_id}:{uuid.uuid4()}"
        
        return user_convs[notebook_id]
    
    def get_history(self, conversation_id: str) -> list:
        """Get conversation history for a specific conversation."""
        return self._conversation_cache.get(conversation_id, [])
    
    def add_turn(self, conversation_id: str, query: str, answer: str) -> None:
        """Add a turn to conversation history."""
        if conversation_id not in self._conversation_cache:
            self._conversation_cache[conversation_id] = []
        self._conversation_cache[conversation_id].append({
            "query": query,
            "answer": answer,
            "turn": len(self._conversation_cache[conversation_id]) + 1
        })
    
    def clear_user_conversations(self, user_id: str) -> int:
        """Clear all conversations for a user."""
        if user_id not in self._user_conversations:
            return 0
        
        count = 0
        for conv_id in self._user_conversations[user_id].values():
            if conv_id in self._conversation_cache:
                del self._conversation_cache[conv_id]
                count += 1
        
        del self._user_conversations[user_id]
        return count
    
    def list_user_conversations(self, user_id: str) -> list[dict]:
        """List all active conversations for a user."""
        if user_id not in self._user_conversations:
            return []
        
        return [
            {
                "notebook_id": nb_id,
                "conversation_id": conv_id,
                "turn_count": len(self._conversation_cache.get(conv_id, [])),
            }
            for nb_id, conv_id in self._user_conversations[user_id].items()
        ]
```

### 2. Per-User Rate Limiting

Distribute the account's rate limit fairly among users:

```python
from threading import Lock
import time

class SharedAccountRateLimiter:
    """Rate limiting for shared account mode."""
    
    def __init__(
        self,
        account_daily_limit: int = 50,  # Total account limit
        max_users: int = 10,             # Expected max concurrent users
        burst_limit: int = 5,            # Max requests per minute per user
    ):
        self.account_daily_limit = account_daily_limit
        self.max_users = max_users
        self.burst_limit = burst_limit
        
        # Per-user fair share
        self.user_daily_limit = max(account_daily_limit // max_users, 5)
        
        self._user_usage: dict[str, list[float]] = {}
        self._lock = Lock()
    
    def check_and_consume(self, user_id: str) -> tuple[bool, str]:
        """Check if user can make a request."""
        with self._lock:
            now = time.time()
            
            if user_id not in self._user_usage:
                self._user_usage[user_id] = []
            
            # Clean old timestamps
            day_ago = now - 86400
            minute_ago = now - 60
            
            self._user_usage[user_id] = [
                ts for ts in self._user_usage[user_id] if ts > day_ago
            ]
            
            timestamps = self._user_usage[user_id]
            
            # Check daily limit
            if len(timestamps) >= self.user_daily_limit:
                return False, f"Daily limit ({self.user_daily_limit}) exceeded"
            
            # Check burst limit
            recent = [ts for ts in timestamps if ts > minute_ago]
            if len(recent) >= self.burst_limit:
                wait_time = 60 - (now - recent[0])
                return False, f"Too many requests. Wait {wait_time:.0f}s"
            
            # Allow and record
            self._user_usage[user_id].append(now)
            remaining = self.user_daily_limit - len(timestamps) - 1
            
            return True, f"OK. {remaining} requests remaining today"
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get usage stats for a user."""
        with self._lock:
            now = time.time()
            day_ago = now - 86400
            
            timestamps = self._user_usage.get(user_id, [])
            daily_usage = len([ts for ts in timestamps if ts > day_ago])
            
            return {
                "user_id": user_id,
                "daily_used": daily_usage,
                "daily_limit": self.user_daily_limit,
                "daily_remaining": self.user_daily_limit - daily_usage,
            }
```

### 3. MCP Tool with User Isolation

```python
from contextvars import ContextVar

# Global state for shared account mode
_shared_client: NotebookLMClient | None = None
_conversation_manager = UserConversationManager()
_rate_limiter = SharedAccountRateLimiter()

def get_shared_client() -> NotebookLMClient:
    """Get the shared NotebookLM client."""
    global _shared_client
    if _shared_client is None:
        cached = load_cached_tokens()
        if not cached:
            raise ValueError("No authentication configured")
        _shared_client = NotebookLMClient(
            cookies=cached.cookies,
            csrf_token=cached.csrf_token,
            session_id=cached.session_id,
        )
    return _shared_client


@mcp.tool()
def notebook_query(
    notebook_id: str,
    query: str,
    user_id: str,  # REQUIRED for conversation isolation
    source_ids: list[str] | None = None,
    new_conversation: bool = False,
) -> dict:
    """Query notebook with user-isolated conversation context.
    
    Args:
        notebook_id: Notebook UUID
        query: Question to ask
        user_id: User identifier (REQUIRED for conversation isolation)
        source_ids: Specific sources to query (default: all)
        new_conversation: Start fresh conversation
    """
    if not user_id:
        return {"status": "error", "error": "user_id required for conversation isolation"}
    
    # Rate limit check
    allowed, msg = _rate_limiter.check_and_consume(user_id)
    if not allowed:
        return {"status": "error", "error": msg}
    
    try:
        client = get_shared_client()
        
        # Get user-scoped conversation
        conv_id = _conversation_manager.get_conversation_id(
            user_id, notebook_id, create_new=new_conversation
        )
        
        # Execute query with user's conversation context
        result = client.query(
            notebook_id=notebook_id,
            query_text=query,
            source_ids=source_ids,
            conversation_id=conv_id,
        )
        
        # Cache the turn for this user
        if result and result.get("answer"):
            _conversation_manager.add_turn(conv_id, query, result["answer"])
        
        history = _conversation_manager.get_history(conv_id)
        
        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "conversation_id": conv_id,
            "user_id": user_id,
            "turn_number": len(history),
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def conversation_list(user_id: str) -> dict:
    """List all active conversations for a user."""
    conversations = _conversation_manager.list_user_conversations(user_id)
    return {"status": "success", "user_id": user_id, "conversations": conversations}


@mcp.tool()
def conversation_clear(user_id: str, notebook_id: str = "") -> dict:
    """Clear conversation history for a user."""
    if notebook_id:
        conv_id = _conversation_manager.get_conversation_id(user_id, notebook_id)
        _conversation_manager._conversation_cache.pop(conv_id, None)
        return {"status": "success", "cleared": 1}
    else:
        count = _conversation_manager.clear_user_conversations(user_id)
        return {"status": "success", "cleared": count}


@mcp.tool()
def rate_limit_status(user_id: str) -> dict:
    """Check rate limit status for a user."""
    return _rate_limiter.get_user_stats(user_id)
```

---

## Open WebUI Integration

### The Challenge

Open WebUI knows who the user is, but the MCP server doesn't receive this information by default.

### Solution: Open WebUI Function Wrapper (Recommended)

Create an Open WebUI Function that automatically injects the user ID into MCP calls.

**Key Insight:** Open WebUI automatically injects a `__user__` dict into Function calls:

```python
__user__ = {
    "id": "user-uuid-here",
    "email": "alice@company.com", 
    "name": "Alice",
    "role": "user",  # or "admin"
}
```

### Complete Open WebUI Function

Go to **Workspace → Functions → Create** and add:

```python
"""
title: NotebookLM Query
description: Query NotebookLM notebooks with automatic user isolation
author: Your Team
version: 1.0
"""

import httpx

class Tools:
    def __init__(self):
        # Adjust to your MCP server URL
        self.mcp_url = "http://localhost:8000"
    
    async def query_notebook(
        self,
        notebook_id: str,
        question: str,
        __user__: dict = {},  # Open WebUI injects this automatically!
    ) -> str:
        """Ask a question about a NotebookLM notebook.
        
        Args:
            notebook_id: The notebook ID (UUID) to query
            question: Your question about the notebook content
        
        Returns:
            AI-generated answer based on notebook sources
        """
        # Extract user ID from Open WebUI's injected context
        user_id = __user__.get("id", "anonymous")
        
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.mcp_url}/mcp",
                json={
                    "tool": "notebook_query",
                    "arguments": {
                        "notebook_id": notebook_id,
                        "query": question,
                        "user_id": user_id,  # Automatically injected!
                    }
                }
            )
            
            result = response.json()
            
            if result.get("status") == "success":
                return result.get("answer", "No answer generated")
            else:
                return f"Error: {result.get('error', 'Unknown error')}"
    
    async def list_notebooks(self, __user__: dict = {}) -> str:
        """List all available NotebookLM notebooks."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_url}/mcp",
                json={"tool": "notebook_list", "arguments": {}}
            )
            
            result = response.json()
            if result.get("status") == "success":
                notebooks = result.get("notebooks", [])
                if not notebooks:
                    return "No notebooks found."
                return "\n".join([
                    f"• **{nb['title']}**\n  ID: `{nb['id']}`"
                    for nb in notebooks
                ])
            return f"Error: {result.get('error')}"
    
    async def new_conversation(
        self,
        notebook_id: str,
        __user__: dict = {},
    ) -> str:
        """Start a fresh conversation with a notebook (clears previous context)."""
        user_id = __user__.get("id", "anonymous")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_url}/mcp",
                json={
                    "tool": "conversation_clear",
                    "arguments": {
                        "user_id": user_id,
                        "notebook_id": notebook_id,
                    }
                }
            )
            return "Conversation cleared. Your next question will start fresh."
    
    async def check_rate_limit(self, __user__: dict = {}) -> str:
        """Check your remaining query quota for today."""
        user_id = __user__.get("id", "anonymous")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_url}/mcp",
                json={
                    "tool": "rate_limit_status",
                    "arguments": {"user_id": user_id}
                }
            )
            
            result = response.json()
            return (
                f"**Rate Limit Status**\n"
                f"- Used today: {result.get('daily_used', 0)}\n"
                f"- Remaining: {result.get('daily_remaining', 0)}\n"
                f"- Daily limit: {result.get('daily_limit', 0)}"
            )
```

### Alternative: System Prompt Injection

If you can't use Functions, configure Open WebUI to inject user context via system prompt:

**Admin Panel → Settings → Interface → Default System Prompt:**

```
You are an AI assistant with access to NotebookLM tools.

IMPORTANT: The current user is: {{USER_NAME}} (ID: {{USER_ID}})

When calling any NotebookLM tool, you MUST include:
- user_id: "{{USER_ID}}"

This ensures conversation history is properly isolated per user.
```

### Open WebUI Template Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{USER_NAME}}` | Display name | "Alice Smith" |
| `{{USER_EMAIL}}` | Email address | "alice@company.com" |
| `{{USER_ID}}` | Unique user ID | "a1b2c3d4-..." |
| `{{USER_ROLE}}` | Role | "user" or "admin" |

---

## Quick Start Guide

### Step 1: Authenticate NotebookLM Account

```bash
# Run authentication (one-time setup)
notebooklm-mcp-auth
```

### Step 2: Start MCP Server

```bash
# Configure for HTTP transport
export NOTEBOOKLM_MCP_TRANSPORT=http
export NOTEBOOKLM_MCP_HOST=0.0.0.0
export NOTEBOOKLM_MCP_PORT=8000

# Start server
notebooklm-mcp
```

### Step 3: Add Open WebUI Function

1. Go to **Workspace → Functions → Create**
2. Paste the Function code from [Open WebUI Integration](#complete-open-webui-function)
3. Click **Save**
4. Enable the function

### Step 4: Test User Isolation

**User Alice** logs in and asks:
> "What are the main topics in notebook abc-123?"

MCP receives: `user_id="alice-uuid"` → Creates conversation `alice-uuid:conv-001`

**User Bob** logs in and asks the same question:

MCP receives: `user_id="bob-uuid"` → Creates separate conversation `bob-uuid:conv-001`

**Alice's follow-up:**
> "Tell me more about the first topic"

MCP uses Alice's conversation history. Bob's context is completely separate.

### Docker Compose Example

```yaml
version: '3.8'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - WEBUI_AUTH=true
    volumes:
      - open-webui-data:/app/backend/data
    depends_on:
      - notebooklm-mcp

  notebooklm-mcp:
    image: notebooklm-mcp:latest
    environment:
      - NOTEBOOKLM_MCP_TRANSPORT=http
      - NOTEBOOKLM_MCP_HOST=0.0.0.0
      - NOTEBOOKLM_MCP_PORT=8000
    volumes:
      - ./auth:/root/.notebooklm-mcp
    ports:
      - "8000:8000"

volumes:
  open-webui-data:
```

---

## When to Use This Approach

### Good Fit ✓

- Team sharing a single NotebookLM Plus subscription
- Internal knowledge base accessible to multiple users
- Development and testing environments
- Users who collaborate on the same notebooks
- Trusted user environment

### Not Recommended ✗

- External/untrusted users (user IDs can be spoofed)
- Strict data isolation requirements
- Compliance requirements (HIPAA, SOC2)
- Users who should not see each other's notebooks

---

## Security Considerations

### 1. User ID Validation

```python
def validate_user_id(user_id: str) -> bool:
    """Validate user ID format."""
    import re
    # Expect UUID format
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, user_id, re.IGNORECASE))
```

### 2. Audit Logging

```python
import logging
logger = logging.getLogger("notebooklm_mcp.audit")

def log_query(user_id: str, notebook_id: str, query: str):
    logger.info(f"Query: user={user_id} notebook={notebook_id} query={query[:50]}...")
```

### 3. Rate Limiting

Already implemented - prevents any single user from consuming the entire account quota.

---

## Summary

| Aspect | Description |
|--------|-------------|
| **Setup Complexity** | Low - single account authentication |
| **Cost** | Low - one NotebookLM subscription for all users |
| **Notebook Visibility** | Shared - all users see all notebooks |
| **Conversation Isolation** | Yes - each user has separate context |
| **Rate Limits** | Distributed fairly per user |
| **Best For** | Teams sharing internal knowledge base |
