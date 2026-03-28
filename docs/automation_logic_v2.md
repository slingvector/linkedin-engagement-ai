# LinkedIn Automation: Profile Scroll & Post Link Copying

This document explains how the automation system (utilizing Appium and ADB) handles LinkedIn profile/feed scrolling and the extraction of post URLs.

## 1. Device Orchestration Layer
The system uses a combination of **Appium** (for UI-level interactions) and **ADB** (for OS-level tasks and speed).

### Wake & Unlock
Before any LinkedIn interaction, the [ADBClient](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/services/adb_client.py#22-235) ensures the device is ready:
- **Wake:** Sends `KEYCODE_WAKEUP` via ADB shell.
- **Unlock:** Performs a swipe gesture to reveal the PIN pad and types the PIN using `adb shell input text`.

### App Lifecycle
- **Launch:** Uses the Android `monkey` command (`adb shell monkey -p com.linkedin.android...`) to force-start LinkedIn from a clean state.
- **Verification:** Waits for specific resource IDs like `com.linkedin.android:id/tab_feed` to ensure the app has loaded the home screen.

## 2. Navigation & Scrolling
The [AppiumReadService](file:///Users/cortex/ventures/linkedin-as-a-service/apps/core_api/app/services/appium_read_service.py#54-493) (or [LinkedInFeedPage](file:///Users/cortex/ventures/RoboticDevice/backend/appium_service/pages/linkedin/feed_page.py#7-129) in the newer architecture) manages the feed state.

### Reaching the Feed
- Ensures the "Home" tab is selected.
- Dismisses common LinkedIn popups (e.g., "Add to home screen", "Payment problematic") by searching for specific button labels like "Not now" or "No thanks" in the XML tree.

### Scrolling Logic
- **Direction:** Swipes from bottom to top (`adb shell input swipe 540 1800 540 600`) to move the content down.
- **Damping:** Includes short pauses (`time.sleep`) after each scroll to allow the Compose UI to stabilize and render new post cards.

## 3. Post Harvesting (Link & Metadata)
The core of the "read flow" is identifying posts and extracting their unique URLs.

### Post Card Detection
The system does not rely on fragile pixel-based detection. Instead, it parses the **UI Automator XML source**:
- Scans for **"More options"** (three-dot menu) buttons, which are unique markers for post cards.
- Extracts engagement metrics (Like/Comment/Repost counts) from adjacent nodes in the XML tree.

### Copy Link Workflow
For each identified post card, the following sequence is executed:
1.  **Menu Trigger:** Taps the center coordinates of the "More options" button.
2.  **Menu Selection:** Searches the resulting bottom sheet/context menu for the text **"Copy link to post"**.
3.  **Fallback:** If the direct link option is missing, it clicks **"Share via"** followed by **"Copy link"** in the Android system share sheet.

### Clipboard Extraction
Since Appium's clipboard support can be inconsistent across Android versions, the system uses a robust **ADB-based retrieval strategy**:
- **Clipper Broadcast:** Sends a broadcast to a helper app (Clipper) to get the current clipboard content.
- **Dumpsys Method:** As a fallback, it queries `adb shell dumpsys clipboard` and uses regex to find the `https://www.linkedin.com/posts/...` URL.

## 4. Data Persistence
Once a URL is extracted, it is deduplicated against a local set of `seen_urls` and sent to the **Ingestion Worker** to be saved into the PostgreSQL database.

---
> [!NOTE]
> This automation is designed to be "read-only" (passive ingestion). It mimics human behavior by maintaining a persistent logged-in profile and using moderate scroll speeds to avoid triggering LinkedIn's anti-scraping detections.
