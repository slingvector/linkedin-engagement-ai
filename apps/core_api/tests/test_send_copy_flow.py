import sys
import os
import time

# Add apps/core_api to path
sys.path.append(os.path.join(os.getcwd(), "apps", "core_api"))

from app.services.appium_read_service import AppiumReadService

DEVICE_UDID = "RZCY110AKDZ"
DEVICE_PIN = "2103"

def main():
    print(f"🧪 Testing Automated 'Send-Copy' Flow on {DEVICE_UDID}...")
    print("💡 NOTE: Appium server appears to be offline. Falling back to Pure ADB (XML-based) mode.")
    
    config = {
        "device_udid": DEVICE_UDID,
        "device_pin": DEVICE_PIN,
        "linkedin_package": "com.linkedin.android",
        "appium_server_url": "http://localhost:4723"
    }
    
    # Initialize service (Singleton)
    svc = AppiumReadService(config)
    
    try:
        # 1. Wake and Navigation (Pure ADB)
        print("🔓 Unlocking and Launching LinkedIn...")
        svc._adb.unlock_device(DEVICE_PIN)
        svc._adb.launch_linkedin()
        time.sleep(8) # Wait for LinkedIn to load
        
        # 2. Extract links using the Pure ADB fallback
        # This uses the SAME 'Rightmost-Sibling' logic as the Appium flow
        print("\n--- Attempting Link Extraction (Pure ADB) ---")
        links = svc.get_feed_links_adb(count=2)
        
        if links:
            print(f"\n🎉 SUCCESS! Extracted {len(links)} links:")
            for i, link in enumerate(links, 1):
                print(f"  {i}. {link}")
        else:
            print("❌ FAILED: Could not extract links via ADB.")
            
    except Exception as e:
        print(f"🔥 Error during test: {e}")
    finally:
        print("\n🏁 test_send_copy_flow.py Finished.")

if __name__ == "__main__":
    main()
