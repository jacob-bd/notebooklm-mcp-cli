import os
from pathlib import Path

# Thư mục / tệp được liệt vào diện nguy hiểm, tuyệt đối không cho phép AI đọc nội dung (tránh Local File Disclosure)
FORBIDDEN_READ_PATHS = [
    Path.home() / ".ssh",
    Path.home() / ".aws",
    Path.home() / ".gnupg",
    Path.home() / ".config" / "gcloud",
    Path("/etc/passwd"),
    Path("/etc/shadow"),
    Path.home() / ".bashrc",
    Path.home() / ".zshrc",
]

def sanitize_input_path(path_str: str) -> Path:
    """Validate that the given path string is safe to read."""
    if not path_str:
        raise ValueError("File path cannot be empty.")

    # Convert to Absolute PATH and Normalize `../`
    path = Path(os.path.expanduser(path_str)).resolve()
    
    # Check forbidden locations
    for forbidden in FORBIDDEN_READ_PATHS:
        # Nếu path truyền vào chính xác là forbidden, HOẶC nằm trong lòng forbidden (.parents)
        if path == forbidden or forbidden in path.parents:
            raise ValueError(f"Security Policy Violation: Access to '{path_str}' is forbidden.")
            
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path_str}")
        
    return path

def sanitize_output_path(filename: str) -> Path:
    """Ensure downloaded files are safely written into a default Sandbox downloads directory."""
    if not filename:
        raise ValueError("Filename cannot be empty.")
        
    # Lấy base name để đánh văng mọi directory traversal attack ../../
    safe_filename = Path(filename).name
    if not safe_filename:
        safe_filename = "downloaded_artifact.txt"
        
    # Mặc định lưu về ~/Downloads/NotebookLM
    downloads_dir = Path.home() / "Downloads" / "NotebookLM"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    return downloads_dir / safe_filename
