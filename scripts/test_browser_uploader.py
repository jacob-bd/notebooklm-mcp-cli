"""
Test BrowserUploader class.
"""
import logging
import sys
from notebooklm_tools.core.uploader import BrowserUploader

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def test():
    uploader = BrowserUploader()
    
    # Use the notebook ID we found earlier (or create one using client if needed)
    notebook_id = "c617901c-b018-4652-a6c9-965540502691"
    file_path = "dummy.pdf"
    
    print(f"Uploading {file_path} to {notebook_id}...")
    try:
        uploader.upload_file(notebook_id, file_path)
        print("Upload successful!")
    except Exception as e:
        print(f"Upload failed: {e}")
        # Print current URL to debug
        current_url = uploader._execute_script("window.location.href")
        print(f"Current URL: {current_url}")
    finally:
        # Don't close immediately so we can see
        # uploader.close()
        pass

if __name__ == "__main__":
    test()
