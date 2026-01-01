import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/hustvl/4DGaussians.git"
DEST_DIR = Path("4DGaussians")

def setup_repo():
    if DEST_DIR.exists():
        print(f"{DEST_DIR} already exists. Updating...")
        subprocess.run(["git", "pull"], cwd=DEST_DIR, check=True)
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=DEST_DIR, check=True)
    else:
        print(f"Cloning {REPO_URL}...")
        subprocess.run(["git", "clone", REPO_URL, str(DEST_DIR)], check=True)
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=DEST_DIR, check=True)
        
    print("Repository setup complete.")
    
    # Try to install submodules requirements if they exist?
    # Usually 4DGaussians has its own requirements.
    
if __name__ == "__main__":
    setup_repo()
