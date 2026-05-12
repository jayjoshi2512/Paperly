"""Run this script ONCE while uvicorn is stopped to reset the Qdrant collection to 1024 dims."""
import shutil
import os

storage_path = "local_qdrant_storage"

if os.path.exists(storage_path):
    shutil.rmtree(storage_path, ignore_errors=True)
    if os.path.exists(storage_path):
        print(f"Could not fully remove {storage_path} (lock file still held?). Try stopping uvicorn first.")
    else:
        print(f"✓ Deleted {storage_path} — will be recreated at 1024 dims on next server start.")
else:
    print("Storage folder not found — nothing to delete.")
