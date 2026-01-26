"""
Script to test file upload via CDP.
"""
import time
import json
import os
from pathlib import Path
from notebooklm_tools.utils.cdp import (
    launch_chrome,
    find_or_create_notebooklm_page,
    execute_cdp_command,
    navigate_to_url,
    get_document_root,
    query_selector
)
from notebooklm_tools.core.auth import load_cached_tokens

def inject_cookies(ws_url, cookies):
    print("Injecting cookies...")
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

def test_upload(file_path):
    file_path = str(Path(file_path).absolute())
    print(f"Testing upload for: {file_path}")
    
    tokens = load_cached_tokens()
    if not tokens:
        print("No tokens found")
        return

    if not launch_chrome(headless=False):
        print("Failed to launch Chrome")
        return

    time.sleep(3)
    page = find_or_create_notebooklm_page()
    if not page:
        print("Failed to find page")
        return
    ws_url = page.get("webSocketDebuggerUrl")

    # 1. Inject & Nav
    inject_cookies(ws_url, tokens.cookies)
    
    notebook_id = "c617901c-b018-4652-a6c9-965540502691"
    url = f"https://notebooklm.google.com/notebook/{notebook_id}"
    print(f"Navigating to {url}...")
    navigate_to_url(ws_url, url)
    
    print("Waiting for load...")
    time.sleep(10)
    
    # 2. Click Add Source
    print("Clicking Add Source...")
    res = execute_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": """
        (function() {
             const btn = document.querySelector('.add-source-button') || 
                         document.querySelector('.upload-button') ||
                         document.querySelector('button[aria-label="Add sources"]');
             if (btn) {
                 btn.click();
                 return true;
             }
             return false;
        })()
        """,
        "returnByValue": True
    })
    if not res.get("result", {}).get("value"):
        print("Could not find/click Add Source button")
        # Try finding ANY button with "Add source" text
        execute_cdp_command(ws_url, "Runtime.evaluate", {
            "expression": """
            const elements = document.querySelectorAll('button, div[role=button]');
            for(const el of elements) {
                if(el.textContent.includes('Add source')) {
                    el.click();
                    break;
                }
            }
            """
        })
    
    time.sleep(2)
    
    # 3. Click PDF/File option
    print("Clicking PDF/File option...")
    execute_cdp_command(ws_url, "Runtime.evaluate", {
        "expression": """
            const options = document.querySelectorAll('button, [role=menuitem]');
            for(const el of options) {
                if(el.textContent.includes('PDF') || el.textContent.includes('File') || el.textContent.includes('Upload')) {
                    el.click();
                    break;
                }
            }
        """
    })
    
    time.sleep(2)
    
    # 4. Find Input and Upload
    print("Looking for input to attach file...")
    
    # We need the nodeId for DOM.setFileInputFiles
    root = get_document_root(ws_url)
    if not root:
        print("Could not get doc root")
        return
        
    input_node_id = query_selector(ws_url, root["nodeId"], "input[type=file]")
    
    if input_node_id:
        print(f"Found input node: {input_node_id}")
        
        # Determine backend node id if needed, but setFileInputFiles takes nodeId since Chrome 90+?
        # Actually protocol says "files" and "nodeId" (or backendNodeId in newer versions?)
        # Let's check the spec or just try nodeId.
        
        print(f"Setting file: {file_path}")
        res = execute_cdp_command(ws_url, "DOM.setFileInputFiles", {
            "files": [file_path],
            "nodeId": input_node_id
        })
        print(f"Upload result: {res}")
        
        # Trigger change event just in case
        execute_cdp_command(ws_url, "Runtime.evaluate", {
            "expression": "document.querySelector('input[type=file]').dispatchEvent(new Event('change', {bubbles: true}))"
        })
        
    else:
        print("No input[type=file] found even after clicking menus")
        
        # Debug: dump what we see
        execute_cdp_command(ws_url, "Runtime.evaluate", {
            "expression": "console.log(document.body.innerHTML)"
        })

if __name__ == "__main__":
    test_upload("dummy.pdf")
