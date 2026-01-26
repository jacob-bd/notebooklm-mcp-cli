"""
Concurrency tests for NotebookLM MCP HTTP transport.

Tests the server's ability to handle multiple concurrent requests safely.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx
import pytest


# Test configuration
MCP_URL = "http://localhost:8000"
MCP_ENDPOINT = f"{MCP_URL}/mcp"
HEALTH_ENDPOINT = f"{MCP_URL}/health"


@pytest.fixture
def mcp_client():
    """Create an HTTP client for MCP server."""
    return httpx.Client(timeout=180.0)


@pytest.fixture
async def async_mcp_client():
    """Create an async HTTP client for MCP server."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        yield client


class TestHTTPConcurrency:
    """Test concurrent request handling for HTTP transport."""

    def test_health_check(self, mcp_client):
        """Verify server is running before concurrency tests."""
        response = mcp_client.get(HEALTH_ENDPOINT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notebooklm-mcp"
        print(f"✓ Server healthy: v{data.get('version')}")

    def test_concurrent_health_checks(self):
        """Test many concurrent health check requests."""
        num_requests = 50

        def make_request(i):
            with httpx.Client() as client:
                start = time.time()
                response = client.get(HEALTH_ENDPOINT, timeout=30.0)
                elapsed = time.time() - start
                return {
                    "request_id": i,
                    "status_code": response.status_code,
                    "elapsed": elapsed,
                    "success": response.status_code == 200
                }

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        avg_response_time = sum(r["elapsed"] for r in results) / len(results)

        print(f"\n{'='*60}")
        print(f"Concurrent Health Checks Test")
        print(f"{'='*60}")
        print(f"Total requests: {num_requests}")
        print(f"Successful: {success_count}/{num_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg response time: {avg_response_time*1000:.2f}ms")
        print(f"Requests/sec: {num_requests/total_time:.2f}")

        assert success_count == num_requests, f"Only {success_count}/{num_requests} succeeded"

    def test_concurrent_notebook_list(self):
        """Test concurrent notebook_list calls (read-only operation)."""
        num_requests = 20

        def make_request(i):
            with httpx.Client() as client:
                start = time.time()
                try:
                    response = client.post(
                        MCP_ENDPOINT,
                        json={
                            "tool": "notebook_list",
                            "arguments": {"max_results": 10}
                        },
                        timeout=60.0
                    )
                    elapsed = time.time() - start
                    data = response.json()

                    return {
                        "request_id": i,
                        "status_code": response.status_code,
                        "elapsed": elapsed,
                        "success": data.get("status") == "success",
                        "count": data.get("count", 0) if data.get("status") == "success" else None,
                        "error": data.get("error") if data.get("status") == "error" else None
                    }
                except Exception as e:
                    return {
                        "request_id": i,
                        "status_code": 0,
                        "elapsed": time.time() - start,
                        "success": False,
                        "error": str(e)
                    }

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        failed = [r for r in results if not r["success"]]

        print(f"\n{'='*60}")
        print(f"Concurrent notebook_list Test (Read-Only)")
        print(f"{'='*60}")
        print(f"Total requests: {num_requests}")
        print(f"Successful: {success_count}/{num_requests}")
        print(f"Failed: {len(failed)}")
        print(f"Total time: {total_time:.2f}s")

        if failed:
            print(f"\nFailure details:")
            for r in failed[:5]:  # Show first 5 failures
                print(f"  Request {r['request_id']}: {r.get('error', 'Unknown error')}")

        # Check for consistency - all successful requests should return same count
        counts = [r["count"] for r in results if r["success"] and r["count"] is not None]
        if counts:
            unique_counts = set(counts)
            print(f"Notebook counts returned: {unique_counts}")
            assert len(unique_counts) == 1, f"Inconsistent counts: {unique_counts}"

        # Should have high success rate for read operations
        assert success_count >= num_requests * 0.9, f"Too many failures: {success_count}/{num_requests}"

    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self, async_mcp_client):
        """Test concurrent requests using async/await."""
        num_requests = 30

        async def make_request(client, i):
            start = time.time()
            try:
                response = await client.post(
                    MCP_ENDPOINT,
                    json={
                        "tool": "notebook_list",
                        "arguments": {"max_results": 5}
                    },
                    timeout=60.0
                )
                elapsed = time.time() - start
                data = response.json()

                return {
                    "request_id": i,
                    "elapsed": elapsed,
                    "success": data.get("status") == "success",
                    "error": data.get("error") if data.get("status") == "error" else None
                }
            except Exception as e:
                return {
                    "request_id": i,
                    "elapsed": time.time() - start,
                    "success": False,
                    "error": str(e)
                }

        start_time = time.time()
        tasks = [make_request(async_mcp_client, i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        success_count = sum(1 for r in results if r["success"])
        avg_time = sum(r["elapsed"] for r in results) / len(results)

        print(f"\n{'='*60}")
        print(f"Async Concurrent Requests Test")
        print(f"{'='*60}")
        print(f"Total requests: {num_requests}")
        print(f"Successful: {success_count}/{num_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Avg response time: {avg_time*1000:.2f}ms")
        print(f"Requests/sec: {num_requests/total_time:.2f}")

        assert success_count >= num_requests * 0.9

    def test_mixed_read_operations(self):
        """Test concurrent mixed read operations."""

        # First, get a notebook to test with
        with httpx.Client() as client:
            response = client.post(
                MCP_ENDPOINT,
                json={"tool": "notebook_list", "arguments": {"max_results": 1}},
                timeout=30.0
            )
            data = response.json()

            if data.get("status") != "success" or not data.get("notebooks"):
                pytest.skip("No notebooks available for testing")

            notebook_id = data["notebooks"][0]["id"]

        def make_mixed_request(i):
            """Alternate between different read operations."""
            with httpx.Client() as client:
                start = time.time()
                try:
                    # Alternate between different tools
                    if i % 3 == 0:
                        payload = {"tool": "notebook_list", "arguments": {"max_results": 5}}
                    elif i % 3 == 1:
                        payload = {"tool": "notebook_get", "arguments": {"notebook_id": notebook_id}}
                    else:
                        payload = {"tool": "source_list_drive", "arguments": {"notebook_id": notebook_id}}

                    response = client.post(MCP_ENDPOINT, json=payload, timeout=60.0)
                    elapsed = time.time() - start
                    data = response.json()

                    return {
                        "request_id": i,
                        "tool": payload["tool"],
                        "elapsed": elapsed,
                        "success": data.get("status") == "success",
                        "error": data.get("error")
                    }
                except Exception as e:
                    return {
                        "request_id": i,
                        "tool": "unknown",
                        "elapsed": time.time() - start,
                        "success": False,
                        "error": str(e)
                    }

        num_requests = 15
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_mixed_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])

        # Group by tool
        by_tool = {}
        for r in results:
            tool = r["tool"]
            if tool not in by_tool:
                by_tool[tool] = {"success": 0, "total": 0}
            by_tool[tool]["total"] += 1
            if r["success"]:
                by_tool[tool]["success"] += 1

        print(f"\n{'='*60}")
        print(f"Mixed Read Operations Test")
        print(f"{'='*60}")
        print(f"Total requests: {num_requests}")
        print(f"Successful: {success_count}/{num_requests}")
        print(f"Total time: {total_time:.2f}s")
        print(f"\nResults by tool:")
        for tool, stats in by_tool.items():
            print(f"  {tool}: {stats['success']}/{stats['total']}")

        assert success_count >= num_requests * 0.8

    def test_concurrent_different_tools(self):
        """Test truly concurrent requests to different tools."""

        def call_tool(tool_name, args):
            with httpx.Client() as client:
                start = time.time()
                try:
                    response = client.post(
                        MCP_ENDPOINT,
                        json={"tool": tool_name, "arguments": args},
                        timeout=60.0
                    )
                    elapsed = time.time() - start
                    data = response.json()
                    return {
                        "tool": tool_name,
                        "elapsed": elapsed,
                        "success": data.get("status") in ["success", "pending_confirmation"],
                        "error": data.get("error")
                    }
                except Exception as e:
                    return {
                        "tool": tool_name,
                        "elapsed": time.time() - start,
                        "success": False,
                        "error": str(e)
                    }

        # Define different tool calls
        tool_calls = [
            ("notebook_list", {"max_results": 10}),
            ("notebook_list", {"max_results": 5}),
            ("notebook_list", {"max_results": 20}),
        ]

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
            futures = [executor.submit(call_tool, tool, args) for tool, args in tool_calls]
            results = [f.result() for f in as_completed(futures)]
        total_time = time.time() - start_time

        success_count = sum(1 for r in results if r["success"])

        print(f"\n{'='*60}")
        print(f"Concurrent Different Tools Test")
        print(f"{'='*60}")
        print(f"Tools tested: {len(tool_calls)}")
        print(f"Successful: {success_count}/{len(tool_calls)}")
        print(f"Total time: {total_time:.2f}s")

        for r in results:
            status = "✓" if r["success"] else "✗"
            print(f"  {status} {r['tool']}: {r['elapsed']*1000:.0f}ms")
            if r.get("error"):
                print(f"      Error: {r['error']}")

        assert success_count == len(tool_calls)

    def test_stress_rapid_requests(self):
        """Stress test with rapid-fire requests."""
        num_requests = 100
        max_workers = 20

        def make_request(i):
            with httpx.Client() as client:
                try:
                    response = client.post(
                        MCP_ENDPOINT,
                        json={"tool": "notebook_list", "arguments": {"max_results": 1}},
                        timeout=30.0
                    )
                    data = response.json()
                    return data.get("status") == "success"
                except Exception:
                    return False

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]
        total_time = time.time() - start_time

        success_count = sum(results)

        print(f"\n{'='*60}")
        print(f"Stress Test - Rapid Requests")
        print(f"{'='*60}")
        print(f"Total requests: {num_requests}")
        print(f"Max workers: {max_workers}")
        print(f"Successful: {success_count}/{num_requests}")
        print(f"Failed: {num_requests - success_count}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Requests/sec: {num_requests/total_time:.2f}")
        print(f"Success rate: {success_count/num_requests*100:.1f}%")

        # Accept 95% success rate for stress test
        assert success_count >= num_requests * 0.95, \
            f"Success rate too low: {success_count/num_requests*100:.1f}%"


class TestThreadSafety:
    """Test thread safety of the global client singleton."""

    def test_client_initialization_race_condition(self):
        """Test if concurrent requests can cause issues with client initialization."""

        # This test simulates the scenario where the server just started
        # and multiple requests arrive before the client is initialized

        def make_request(i):
            with httpx.Client() as client:
                try:
                    response = client.post(
                        MCP_ENDPOINT,
                        json={"tool": "notebook_list", "arguments": {}},
                        timeout=60.0
                    )
                    data = response.json()
                    return {
                        "id": i,
                        "success": data.get("status") in ["success", "error"],
                        "has_error": data.get("status") == "error",
                        "error": data.get("error")
                    }
                except Exception as e:
                    return {
                        "id": i,
                        "success": False,
                        "has_error": True,
                        "error": str(e)
                    }

        # Fire off requests simultaneously
        num_requests = 10
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]

        success_count = sum(1 for r in results if r["success"])
        errors = [r["error"] for r in results if r["has_error"] and r["error"]]

        print(f"\n{'='*60}")
        print(f"Client Initialization Race Condition Test")
        print(f"{'='*60}")
        print(f"Simultaneous requests: {num_requests}")
        print(f"Successful: {success_count}/{num_requests}")

        if errors:
            print(f"\nErrors encountered:")
            unique_errors = set(errors)
            for err in unique_errors:
                count = errors.count(err)
                print(f"  ({count}x) {err}")

        # All requests should complete without crashes
        assert success_count == num_requests


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_concurrent_http.py -v -s
    pytest.main([__file__, "-v", "-s"])
