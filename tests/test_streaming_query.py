#!/usr/bin/env python3
"""
Standalone test script for NotebookLM Query Endpoint streaming response.

This script demonstrates real-time streaming of query responses, showing both
"thinking steps" (type 2) and answer chunks (type 1) as they arrive from the API.

Usage:
    python tests/test_streaming_query.py <notebook_id> [query]
    
Example:
    python tests/test_streaming_query.py abc123-def456 "What are the main themes?"
    
Requirements:
    - Must have authenticated using: notebooklm-mcp-auth
    - Notebook must exist and have at least one source
"""

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import AsyncIterator

import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from notebooklm_mcp.auth import load_cached_tokens
from notebooklm_mcp.api_client import NotebookLMClient


class StreamingStats:
    """Track streaming performance metrics."""
    
    def __init__(self):
        self.start_time: float = 0
        self.first_chunk_time: float = 0
        self.thinking_chunks: int = 0
        self.answer_chunks: int = 0
        self.total_bytes: int = 0
        self.chunk_times: list[float] = []
        
    def start(self):
        """Mark the start of the request."""
        self.start_time = time.time()
        
    def mark_first_chunk(self):
        """Mark when first chunk arrives."""
        if self.first_chunk_time == 0:
            self.first_chunk_time = time.time()
            
    def add_chunk(self, is_answer: bool, byte_count: int):
        """Record a chunk arrival."""
        if is_answer:
            self.answer_chunks += 1
        else:
            self.thinking_chunks += 1
        self.total_bytes += byte_count
        self.chunk_times.append(time.time() - self.start_time)
        
    def get_summary(self) -> dict:
        """Get performance summary."""
        total_time = time.time() - self.start_time
        ttfc = self.first_chunk_time - self.start_time if self.first_chunk_time else 0
        
        return {
            "total_time": round(total_time, 2),
            "time_to_first_chunk": round(ttfc, 2),
            "thinking_chunks": self.thinking_chunks,
            "answer_chunks": self.answer_chunks,
            "total_chunks": self.thinking_chunks + self.answer_chunks,
            "total_bytes": self.total_bytes,
            "avg_chunk_interval": round(total_time / max(1, len(self.chunk_times)), 3),
        }


async def stream_query(
    client: NotebookLMClient,
    notebook_id: str,
    query_text: str,
    source_ids: list[str],
) -> AsyncIterator[dict]:
    """
    Stream query response chunks in real-time.
    
    Yields dictionaries with:
    - type: "thinking" or "answer"
    - text: The chunk text content
    - timestamp: Relative time from request start
    - raw_type: Original type indicator (1 or 2)
    """
    import uuid
    
    # Get HTTP client
    http_client = await client._get_client()
    
    # Generate conversation ID
    conversation_id = str(uuid.uuid4())
    
    # Build source IDs structure: [[[sid]]] for each source
    sources_array = [[[sid]] for sid in source_ids]
    
    # Query params structure (matching api_client.py)
    params = [
        sources_array,
        query_text,
        None,  # No conversation history for new conversation
        [2, None, [1]],
        conversation_id,
    ]
    
    # Build request body (matching api_client.py format)
    params_json = json.dumps(params, separators=(",", ":"))
    f_req = [None, params_json]
    f_req_json = json.dumps(f_req, separators=(",", ":"))
    
    body_parts = [f"f.req={urllib.parse.quote(f_req_json, safe='')}"]
    if client.csrf_token:
        body_parts.append(f"at={urllib.parse.quote(client.csrf_token, safe='')}")
    body = "&".join(body_parts) + "&"
    
    # Build URL with query parameters
    url_params = {
        "bl": os.environ.get("NOTEBOOKLM_BL", "boq_labs-tailwind-frontend_20260108.06_p0"),
        "hl": "en",
        "_reqid": str(100000),
        "rt": "c",
    }
    if client._session_id:
        url_params["f.sid"] = client._session_id
        
    query_string = urllib.parse.urlencode(url_params)
    url = f"{client.BASE_URL}{client.QUERY_ENDPOINT}?{query_string}"
    
    # Stream the response
    start_time = time.time()
    
    async with http_client.stream("POST", url, content=body, timeout=120.0) as response:
        response.raise_for_status()
        
        # Process line by line
        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk
            
            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                
                if not line:
                    continue
                    
                # Skip anti-XSSI prefix
                if line.startswith(")]}'"):
                    continue
                    
                # Try to parse as byte count (indicates next line is JSON chunk)
                try:
                    byte_count = int(line)
                    # Byte count line, wait for next line with actual JSON
                    continue
                except ValueError:
                    pass
                    
                # Try to parse as JSON chunk
                chunk_data = parse_chunk(line)
                if chunk_data:
                    chunk_data["timestamp"] = round(time.time() - start_time, 2)
                    yield chunk_data


def parse_chunk(json_str: str) -> dict | None:
    """
    Parse a JSON chunk and extract text and type.
    
    Chunk structure:
    [["wrb.fr", null, "<nested_json>", ...]]
    
    Nested JSON contains:
    [["text", null, [...], null, [type_info]]]
    where type_info ends with 1 (answer) or 2 (thinking)
    
    Returns dict with:
    - type: "thinking" or "answer"
    - text: The chunk text
    - raw_type: Original type indicator (1 or 2)
    """
    try:
        parsed = json.loads(json_str)
        
        # Navigate structure: [["wrb.fr", null, nested_json, ...]]
        if not isinstance(parsed, list) or len(parsed) == 0:
            return None
            
        outer = parsed[0]
        if not isinstance(outer, list) or len(outer) < 3:
            return None
            
        # The third element is the nested JSON string
        nested_json_str = outer[2]
        if not isinstance(nested_json_str, str):
            return None
            
        # Parse nested JSON
        nested = json.loads(nested_json_str)
        if not isinstance(nested, list) or len(nested) == 0:
            return None
            
        # Get the first element of nested structure
        content = nested[0]
        if not isinstance(content, list) or len(content) < 5:
            return None
            
        # Extract text (position 0) and type info (position 4)
        text = content[0]
        type_info = content[4]
        
        if not isinstance(text, str) or not isinstance(type_info, list):
            return None
            
        # Type indicator is last element of type_info array
        type_indicator = type_info[-1] if type_info else None
        
        # Map type: 1 = answer, 2 = thinking
        if type_indicator == 1:
            chunk_type = "answer"
        elif type_indicator == 2:
            chunk_type = "thinking"
        else:
            chunk_type = "unknown"
            
        return {
            "type": chunk_type,
            "text": text,
            "raw_type": type_indicator,
        }
        
    except (json.JSONDecodeError, IndexError, TypeError, KeyError):
        return None


def format_chunk_output(chunk: dict, show_timestamp: bool = True) -> str:
    """Format a chunk for console output with color and emoji."""
    emoji = "🤔" if chunk["type"] == "thinking" else "💡"
    type_label = chunk["type"].upper()
    timestamp_str = f"[{chunk['timestamp']}s]" if show_timestamp else ""
    
    # Truncate long text for cleaner output
    text = chunk["text"]
    if len(text) > 200:
        text = text[:197] + "..."
        
    return f"{emoji} {type_label} {timestamp_str}: {text}"


async def get_notebook_sources(client: NotebookLMClient, notebook_id: str) -> list[str]:
    """Get all source IDs from a notebook."""
    notebook_data = await client.get_notebook(notebook_id)
    source_ids = client._extract_source_ids_from_notebook(notebook_data)
    
    if not source_ids:
        print(f"❌ No sources found in notebook {notebook_id}")
        print("   Add sources to the notebook before querying.")
        sys.exit(1)
        
    return source_ids


async def test_streaming_query(notebook_id: str, query: str, verbose: bool = False):
    """
    Test streaming query endpoint with real-time output.
    
    Args:
        notebook_id: The notebook UUID to query
        query: The question to ask
        verbose: Show detailed chunk information
    """
    print("=" * 80)
    print("NotebookLM Streaming Query Test")
    print("=" * 80)
    
    # Load authentication tokens
    print("\n🔑 Loading authentication tokens...")
    tokens = load_cached_tokens()
    if not tokens:
        print("❌ No cached authentication tokens found.")
        print("   Run 'notebooklm-mcp-auth' to authenticate.")
        sys.exit(1)
        
    print(f"✅ Loaded tokens (extracted {int(time.time() - tokens.extracted_at)}s ago)")
    
    # Initialize client
    print("\n🔧 Initializing API client...")
    client = NotebookLMClient(
        cookies=tokens.cookies,
        csrf_token=tokens.csrf_token,
        session_id=tokens.session_id,
    )
    
    try:
        await client._ensure_initialized()
        print("✅ Client initialized")
        
        # Get notebook sources
        print(f"\n📚 Fetching sources from notebook {notebook_id}...")
        source_ids = await get_notebook_sources(client, notebook_id)
        print(f"✅ Found {len(source_ids)} source(s)")
        
        # Start streaming query
        print(f"\n❓ Query: {query}")
        print("-" * 80)
        
        stats = StreamingStats()
        
        # Log request start time
        request_start = time.time()
        print(f"🚀 Request started at: {time.strftime('%H:%M:%S', time.localtime(request_start))}.{int((request_start % 1) * 1000):03d}")
        print("📡 Streaming response (press Ctrl+C to stop)...\n")
        
        stats.start()
        
        thinking_text = []
        answer_text = []
        first_response_logged = False
        
        async for chunk in stream_query(client, notebook_id, query, source_ids):
            stats.mark_first_chunk()
            
            # Log first response received
            if not first_response_logged:
                first_response_time = time.time()
                elapsed = first_response_time - request_start
                print(f"\n⚡ First response received at: {time.strftime('%H:%M:%S', time.localtime(first_response_time))}.{int((first_response_time % 1) * 1000):03d}")
                print(f"   Time to first response: {elapsed:.3f}s\n")
                first_response_logged = True
            
            # Track chunk
            is_answer = chunk["type"] == "answer"
            stats.add_chunk(is_answer, len(chunk["text"]))
            
            # Store text for final summary
            if is_answer:
                answer_text.append(chunk["text"])
            else:
                thinking_text.append(chunk["text"])
            
            # Print chunk
            if verbose:
                print(format_chunk_output(chunk))
            else:
                # Simplified output - just show dots for thinking, text for answers
                if is_answer:
                    print(f"\n💡 {chunk['text']}")
                else:
                    print(".", end="", flush=True)
        
        # Log completion time
        request_end = time.time()
        total_elapsed = request_end - request_start
        print(f"\n\n✅ Response completed at: {time.strftime('%H:%M:%S', time.localtime(request_end))}.{int((request_end % 1) * 1000):03d}")
        print(f"   Total request time: {total_elapsed:.3f}s")
        
        # Print summary
        print("\n")
        print("=" * 80)
        print("📊 Streaming Summary")
        print("=" * 80)
        
        summary = stats.get_summary()
        print(f"\n⏱️  Timing Breakdown:")
        print(f"   └─ Request start → First response: {summary['time_to_first_chunk']:.3f}s")
        print(f"   └─ Total request duration: {summary['total_time']:.3f}s")
        print(f"\n📦 Chunks Received:")
        print(f"   └─ Thinking chunks: {summary['thinking_chunks']}")
        print(f"   └─ Answer chunks: {summary['answer_chunks']}")
        print(f"   └─ Total chunks: {summary['total_chunks']}")
        print(f"\n📊 Data Transfer:")
        print(f"   └─ Total bytes: {summary['total_bytes']:,}")
        print(f"   └─ Avg chunk interval: {summary['avg_chunk_interval']:.3f}s")
        
        # Show collected text
        if thinking_text:
            print(f"\n🤔 Thinking steps ({len(thinking_text)}):")
            for i, text in enumerate(thinking_text, 1):
                preview = text[:100] + "..." if len(text) > 100 else text
                print(f"   {i}. {preview}")
                
        if answer_text:
            print(f"\n💡 Final answer ({len(answer_text)} chunks):")
            full_answer = " ".join(answer_text)
            print(f"\n{full_answer}\n")
        
        print("=" * 80)
        print("✅ Test completed successfully")
        
    finally:
        await client.close()


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Test NotebookLM streaming query endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic query
  python tests/test_streaming_query.py abc123 "What are the main themes?"
  
  # Verbose output (show all chunks)
  python tests/test_streaming_query.py abc123 "Compare the sources" --verbose
  
  # Complex multi-source query
  python tests/test_streaming_query.py abc123 "Compare and contrast the main arguments across all sources" 
        """,
    )
    
    parser.add_argument(
        "notebook_id",
        help="Notebook UUID to query",
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        default="What are the main themes discussed in these sources?",
        help="Question to ask (default: generic themes question)",
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed chunk information as they arrive",
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(test_streaming_query(args.notebook_id, args.query, args.verbose))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
