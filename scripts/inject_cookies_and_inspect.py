"""
Script to launch Chrome, inject saved cookies, and inspect DOM.
"""
import time
import json
from pathlib import Path
from notebooklm_tools.utils.cdp import (
    launch_chrome,
    find_or_create_notebooklm_page,
    execute_cdp_command,
    get_page_html,
    navigate_to_url
)
from notebooklm_tools.core.auth import load_cached_tokens

def inject_cookies(ws_url, cookies):
    print("Injecting cookies into browser...")
    for name, value in cookies.items():
        execute_cdp_command(ws_url, "Network.setCookie", {
            "name": name,
            "value": value,
            "domain": ".google.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None"
        })
    print(f"Injected {len(cookies)} cookies.")

def inspect_dom():
    tokens = load_cached_tokens()
    if not tokens:
        print("No tokens found in auth.json. Cannot inject.")
        return

    print("Launching Chrome...")
    # headless=False so user can see what's happening
    if not launch_chrome(headless=False):
        print("Failed to launch Chrome")
        return

    time.sleep(3)
    
    # We need to connect to ANY page first to set cookies
    # NotebookLM page might redirect to login immediately, so we race it or reload after
    page = find_or_create_notebooklm_page()
    if not page:
        print("Failed to find/create page")
        return
        
    ws_url = page.get("webSocketDebuggerUrl")
    print(f"Connected to page: {page.get('title')}")

    # 1. Inject Cookies
    inject_cookies(ws_url, tokens.cookies)
    
    # 2. Reload/Navigate to NotebookLM to apply cookies
    print("Reloading NotebookLM with injected cookies...")
    navigate_to_url(ws_url, "https://notebooklm.google.com/")
    time.sleep(5)
    
    # 3. Create Notebook via API (faster/reliable)
    notebook_id = "c617901c-b018-4652-a6c9-965540502691" # Fallback from previous run
    
    print("Creating test notebook for inspection...")
    try:
        from notebooklm_tools.core.client import NotebookLMClient
        # Bypass initial refresh to avoid auth error if possible, or just catch it
        client = NotebookLMClient(tokens.cookies) 
        notebook = client.create_notebook("Upload Inspection Test")
        notebook_id = notebook.id
        print(f"Created notebook: {notebook.id}")
    except Exception as e:
        print(f"Failed to create notebook via API: {e}")
        print(f"Using fallback/existing notebook: {notebook_id}")
    
    if notebook_id:
        notebook_url = f"https://notebooklm.google.com/notebook/{notebook_id}"
        print(f"Navigating to: {notebook_url}")
        navigate_to_url(ws_url, notebook_url)
        
        print("Waiting 10s for page load and UI rendering...")
        time.sleep(10)

    # 4. Dump HTML
    print("Capturing HTML...")
    html = get_page_html(ws_url)
    Path("dom_with_cookies.html").write_text(html)
    print("Saved to dom_with_cookies.html")
    
    # 5. Click "Add Source" and Look for File Input
    print("\nClicking 'Add source' and searching for file inputs...")
    result = execute_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": """
        (async function() {
            function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
            
            // Find the Add Source button
            const addBtn = document.querySelector('.add-source-button') || 
                          document.querySelector('.upload-button') ||
                          document.querySelector('button[aria-label="Add sources"]');
            
            if (addBtn) {
                console.log("Found add button, clicking...");
                addBtn.click();
                await sleep(2000); // Wait for menu/dialog
            } else {
                console.log("No add button found");
            }

            // Now look for file inputs again (often created dynamically)
            const inputs = Array.from(document.querySelectorAll('input[type=file]')).map(el => ({
                id: el.id,
                className: el.className,
                accept: el.accept,
                outerHTML: el.outerHTML
            }));
            
            // Look for "PDF / Text file" options in the menu that might trigger the input
            const menuOptions = Array.from(document.querySelectorAll('button, [role=menuitem]'))
                .filter(el => el.textContent.includes('PDF') || el.textContent.includes('File') || el.textContent.includes('Upload'))
                .map(el => ({
                    text: el.textContent.trim(),
                    className: el.className
                }));

            return { inputs, menuOptions };
        })()
        """,
        "awaitPromise": True,
        "returnByValue": True
    })
    
    data = result.get("result", {}).get("value", {})
    print(json.dumps(data, indent=2))
    
    # If we found menu options but no input, trying clicking the "PDF" option
    if not data.get("inputs") and data.get("menuOptions"):
        print("\nFound menu options. Trying to click 'PDF' option...")
        result = execute_cdp_command(ws_url, "Runtime.evaluate", {
            "expression": """
            (async function() {
                function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
                
                const pdfBtn = Array.from(document.querySelectorAll('button, [role=menuitem]'))
                    .find(el => el.textContent.includes('PDF') || el.textContent.includes('Upload'));
                
                if (pdfBtn) {
                    pdfBtn.click();
                    await sleep(2000);
                }
                
                return Array.from(document.querySelectorAll('input[type=file]')).map(el => ({
                    id: el.id,
                    outerHTML: el.outerHTML
                }));
            })()
            """,
            "awaitPromise": True,
            "returnByValue": True
        })
        print("After clicking PDF option:")
        print(json.dumps(result.get("result", {}).get("value"), indent=2))

    print("\nDONE. Check chrome window to see if you are logged in.")

if __name__ == "__main__":
    inspect_dom()
