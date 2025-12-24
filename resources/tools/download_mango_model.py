import os
import shutil
from huggingface_hub import snapshot_download

def download_mango():
    repo_id = "jrodriiguezg/mango-t5-770m"
    target_dir = os.path.join(os.getcwd(), "MANGOT5")
    
    print(f"Downloading {repo_id} to {target_dir}...")
    
    try:
        # Download the snapshot
        path = snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False, # We want real files
            ignore_patterns=[".gitattributes", "README.md"] 
        )
        print(f"Successfully downloaded MANGO T5 to {path}")
        
    except Exception as e:
        print(f"Error downloading model: {e}")
        exit(1)

if __name__ == "__main__":
    download_mango()
