import sys
import os
import time
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_manager import SyncManager

# Setup basic logging to see output
logging.basicConfig(level=logging.INFO)

def test_sync():
    print("Testing SyncManager...")
    
    # 1. Test Sync Disabled/Enabled logic (implicit in config)
    from config import PB_SYNC_ENABLED, PB_URL
    print(f"Sync Enabled: {PB_SYNC_ENABLED}")
    print(f"PB URL: {PB_URL}")

    # 2. Test Get Token (should not crash even if fail)
    print("Attempting to get token...")
    token = SyncManager.get_token()
    if token:
        print(f"Token received: {token[:10]}...")
    else:
        print("No token received (expected if PB is down or invalid creds).")

    # 3. Test Sync Data (Fire and forget)
    print("Attempting sync_data call...")
    try:
        SyncManager.sync_data("projects", {"project_name": "TestProject_Integration"}, record_id="TestProject_Integration")
        print("sync_data called successfully (thread started).")
    except Exception as e:
        print(f"sync_data CRASHED: {e}")

    # Wait a bit to let thread run if it works
    time.sleep(2)
    print("Test finished.")

if __name__ == "__main__":
    test_sync()
