"""
Script to inspect NotebookLM DOM for file upload selectors.
"""
import time
import json
from pathlib import Path
from notebooklm_tools.utils.cdp import (
    launch_chrome,
    get_debugger_url,
    find_or_create_notebooklm_page,
    execute_cdp_command,
    get_page_html,
    navigate_to_url
)
from notebooklm_tools.core.auth import load_cached_tokens

def inspect_dom():
    print("Launching Chrome for DOM inspection...")
    if not launch_chrome(headless=False):
        print("Failed to launch Chrome")
        return

    tokens = load_cached_tokens()
    if not tokens:
        print("No tokens found. Login first.")
        return

    print("Connecting to Chrome...")
    time.sleep(2)
    
    page = find_or_create_notebooklm_page()
    if not page:
        print("Failed to find/create page")
        return
        
    ws_url = page.get("webSocketDebuggerUrl")
    print(f"Connected to page: {page.get('title')}")

    print("Creating test notebook for inspection...")
    from notebooklm_tools.core.client import NotebookLMClient
    client = NotebookLMClient(tokens.cookies)
    try:
        notebook = client.create_notebook("Upload Inspection Test")
        print(f"Created notebook: {notebook.id}")
        
        notebook_url = f"https://notebooklm.google.com/notebook/{notebook.id}"
        print(f"Navigating to: {notebook_url}")
        navigate_to_url(ws_url, notebook_url)
        time.sleep(5) # Wait for load
    except Exception as e:
        print(f"Failed to create/nav to notebook: {e}")
        # Fallback to existing page
        pass

    # Get HTML
    print("Capturing HTML...")
    html = get_page_html(ws_url)
    
    # Save to file for analysis
    Path("dom_dump.html").write_text(html)
    print("Saved to dom_dump.html")
    
    # Analyze for potential upload selectors
    print("\nSearching for file inputs...")
    
    # Check for file input
    result = execute_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": "document.querySelectorAll('input[type=file]').length"
    })
    count = result.get("result", {}).get("value", 0)
    print(f"Found {count} file inputs")
    
    if count > 0:
        # Get details
        result = execute_cdp_command(ws_url, "Runtime.evaluate", {
            "expression": """
            Array.from(document.querySelectorAll('input[type=file]')).map(el => ({
                id: el.id,
                className: el.className,
                accept: el.accept,
                outerHTML: el.outerHTML
            }))
            """,
            "returnByValue": True
        })
        print(json.dumps(result.get("result", {}).get("value"), indent=2))
        
    # Check for "Add source" buttons
    print("\nSearching for 'Add source' text...")
    result = execute_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": """
        (function() {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            const matches = [];
            while(node = walker.nextNode()) {
                if(node.textContent.includes('Add source') || node.textContent.includes('Upload')) {
                    matches.push({
                        text: node.textContent,
                        parentTag: node.parentElement.tagName,
                        parentClass: node.parentElement.className
                    });
                }
            }
            return matches;
        })()
        """,
        "returnByValue": True
    })
    print(json.dumps(result.get("result", {}).get("value"), indent=2))

if __name__ == "__main__":
    inspect_dom()
