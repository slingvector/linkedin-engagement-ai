"""
AppiumReadService — LinkedIn Feed Reader (Appium/ADB).

Singleton Appium session that:
  1. Wakes the device and opens LinkedIn
  2. Scrolls the home feed N times
  3. For each post card: long-press → "Copy link to post" → reads clipboard
  4. Returns a deduplicated list of post URLs for the ingestion worker to process

Pattern mirrors the Instagram write flow (appium_posting_service.py) but is
read-only — no content is ever posted or modified.
"""

import os
import re
import time
import xml.etree.ElementTree as ET
import structlog
from typing import Any, ClassVar, Dict, List, Optional
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException

logger = structlog.get_logger(__name__)

# ─── Timing constants (seconds) ──────────────────────────────────────────────
WAIT_SHORT  = 3
WAIT_MEDIUM = 8
WAIT_LONG   = 15
# ─────────────────────────────────────────────────────────────────────────────

# LinkedIn Android identifiers (confirmed from AOSP XML recordings)
LINKEDIN_PACKAGE  = "com.linkedin.android"
LINKEDIN_ACTIVITY = "com.linkedin.android.splash.SplashActivity"

# Feed tab identifiers (LinkedIn bottom nav home item)
FEED_TAB_IDS = [
    "com.linkedin.android:id/tab_feed",  # Confirmed on Samsung SM-S938B
    "com.linkedin.android:id/nav_home",
    "com.linkedin.android:id/home_tab",
]

# Feed tab content-desc for accessibility fallback
FEED_TAB_LABELS = ["Home 1 of 5", "Home"]

# Labels for copy link menu item (in context menu)
COPY_LINK_LABELS = [
    "Copy link to post",
    "Copy link",  # Shortened version in some regions/versions
    "Share via"   # Fallback to get to Copy link
]

# Post card markers in Compose UI
CARD_MARKER_LABELS = ["View more options", "more options"]


class AppiumReadService:
    """
    Singleton Appium session manager for LinkedIn feed reading.
    """

    _instance: ClassVar[Optional["AppiumReadService"]] = None
    _driver: Any = None
    _config: Dict[str, Any] = {}
    _adb: Any = None

    def __new__(cls, config: Optional[Dict[str, Any]] = None) -> "AppiumReadService":
        if cls._instance is None:
            instance = super(AppiumReadService, cls).__new__(cls)
            instance._driver = None
            instance._config = config or {}
            from app.services.adb_client import ADBClient
            # ADBClient is now a singleton, so this just gets the instance
            instance._adb = ADBClient(
                device_udid=instance._config.get("device_udid", ""),
                adb_executable=instance._config.get("adb_executable", "adb"),
            )
            instance._initialized = False # Track if start_session has been called
            cls._instance = instance
        return cls._instance

    @property
    def device(self) -> "AppiumReadService":
        """Alias to support self.device terminology in snippets."""
        return self

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def start_session(self) -> None:
        """Initialize the Appium driver session with retries."""
        if self._driver:
            try:
                # Check if session is still alive
                _ = self._driver.orientation
                return
            except Exception:
                logger.info("Existing Appium session is dead. Restarting...")
                self._driver = None

        from appium import webdriver
        from appium.options.android import UiAutomator2Options
        from selenium.common.exceptions import WebDriverException
        
        cfg = self._config
        appium_host = cfg.get("appium_host", "http://localhost:4723").replace("/wd/hub", "").rstrip("/")
        
        options = UiAutomator2Options()
        options.app_package            = cfg.get("linkedin_package", LINKEDIN_PACKAGE)
        options.app_activity           = cfg.get("linkedin_activity", LINKEDIN_ACTIVITY)
        options.no_reset               = True
        options.new_command_timeout    = cfg.get("new_command_timeout", 120)
        options.auto_grant_permissions = True
        options.set_capability("appium:clearSystemFiles", True)
        options.set_capability("appium:waitForIdleTimeout", 1000) # 1s calibration for S24
        options.set_capability("appium:ignoreUnimportantViews", True)
        options.set_capability("appium:disableIdLocatorAutocompletion", True)
        
        device_udid = cfg.get("device_udid", "")
        if device_udid:
            options.udid = device_udid

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self._adb.wake_screen()
                    time.sleep(3)
                self._driver = webdriver.Remote(appium_host, options=options)
                self._driver.implicitly_wait(5)
                logger.info("✅ Appium read session connected.")
                return
            except (WebDriverException, Exception) as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Appium failed after {max_retries} attempts.") from e
                time.sleep(5)

    def end_session(self) -> None:
        """Close the Appium driver session."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("Appium session ended.")
            except Exception as e:
                logger.warning(f"Error ending Appium session: {e}")
            finally:
                self._driver = None

    def get_page_source(self) -> str:
        """Returns the current page source (XML)."""
        if self._driver:
            return self._driver.page_source
        return ""

    def take_screenshot(self, filename: str) -> bool:
        """Saves a screenshot to the specified path."""
        if self._driver:
            try:
                self._driver.get_screenshot_as_file(filename)
                logger.info(f"Screenshot saved to {filename}")
                return True
            except Exception as e:
                logger.warning(f"Failed to take screenshot: {e}")
        return False

    def _log_debug_state(self, label: str):
        """Helper to dump state for debugging on failure."""
        timestamp = int(time.time())
        xml_file = f"/tmp/appium_debug_{label}_{timestamp}.xml"
        png_file = f"/tmp/appium_debug_{label}_{timestamp}.png"
        
        source = self.get_page_source()
        with open(xml_file, "w") as f:
            f.write(source)
            
        self.take_screenshot(png_file)
        logger.info(f"Debug state dumped: {xml_file}, {png_file}")

    def list_ui_elements(self):
        """Debug helper to list all elements with IDs or text/desc."""
        if not self._driver:
            return
        elements = self._driver.find_elements(AppiumBy.XPATH, "//*[@resource-id or @text or @content-desc]")
        logger.info(f"Found {len(elements)} actionable elements.")
        for el in elements[:50]: # First 50 for brevity
            try:
                rid = el.get_attribute("resource-id")
                txt = el.get_attribute("text")
                desc = el.get_attribute("content-desc")
                if rid or txt or desc:
                    logger.info(f"Element: ID={rid}, Text={txt}, Desc={desc}")
            except:
                continue

    def navigate_to_feed(self) -> None:
        logger.info("Navigating to LinkedIn Home Feed...")
        try:
            # Skip dumpsys/introspection - just ensure focus and tap home
            self._adb.unlock_device(pin=self._config.get("device_pin"))
            self._adb.launch_linkedin(package=self._config.get("linkedin_package", LINKEDIN_PACKAGE))
            time.sleep(WAIT_LONG)

            # Fast Path: Check if Home tab is visible via Appium (Fast Scan)
            logger.info("Heartbeat: Checking Home tab via Fast Scan...")
            found_home = False
            for tab_id in FEED_TAB_IDS:
                try:
                    # Use a very short timeout - we don't want to hang here
                    self._driver.implicitly_wait(1)
                    if self._driver.find_elements(AppiumBy.ID, tab_id):
                        found_home = True
                        break
                except Exception:
                    continue
                finally:
                    self._driver.implicitly_wait(5)
            
            if found_home:
                logger.info("LinkedIn Feed detected immediately via Appium. Skipping modal dismiss loop.")
            else:
                for label in ["Not now", "Skip", "Close", "Dismiss"]:
                    if self._tap_by_text_xml(label, timeout=2, exact_match=True):
                        time.sleep(1)

            self._tap_home_tab()
            logger.info("LinkedIn Home Feed is active.")
        except Exception as e:
            logger.exception("navigate_to_feed_failed", error=str(e))
            raise

    def _tap_home_tab(self) -> bool:
        for tab_id in FEED_TAB_IDS:
            try:
                el = self._driver.find_element(AppiumBy.ID, tab_id)
                if el:
                    el.click()
                    return True
            except Exception:
                continue
        for label in FEED_TAB_LABELS:
            if self._tap_by_text_xml(label, timeout=3, exact_match=False):
                return True
        self._adb.tap(144, 2960) # Fallback coordinate for S24 Ultra
        return False

    def click_text(self, text: str, timeout: int = 5) -> bool:
        """Taps an element matching the given text."""
        return self._tap_by_text_xml(text, timeout=timeout, exact_match=False)

    def click_element_by_id(self, rid: str, timeout: int = 5) -> bool:
        """Taps an element matching the given resource ID."""
        try:
            self._driver.implicitly_wait(timeout)
            el = self._driver.find_element(AppiumBy.ID, rid)
            if el:
                el.click()
                return True
        except Exception:
            pass
        finally:
            self._driver.implicitly_wait(5)
        return False

    def scroll_down(self):
        """Scrolls the feed down (content scrolls up)."""
        self._adb.scroll_up(distance=1400, duration_ms=800)

    def _press_back(self):
        """Helper to press BACK key via Appium or ADB."""
        try:
            self._driver.press_keycode(4) # Android BACK
        except Exception:
            self._adb.press_back()

    def _press_home(self):
        """Helper to press HOME key via Appium or ADB."""
        try:
            self._driver.press_keycode(3) # Android HOME
        except Exception:
            self._adb.press_home()

    def scroll_and_collect_urls(self, scroll_count: int = 10) -> List[Dict[str, Any]]:
        """
        Main entry point for feed ingestion.
        Uses the 'Send-Copy' strategy for reliable URL extraction.
        """
        self.dismiss_popups()
        
        links = self.get_feed_links(count=scroll_count)
        
        # Convert to format expected by worker
        return [{"url": link, "reactions": 0, "comments": 0, "reposts": 0} for link in links]

    def dismiss_popups(self) -> bool:
        """Identifies and dismisses blocking popups like Ads or Premium Prompts."""
        popups_dismissed = False
        popup_id = "com.linkedin.android:id/ad_non_modal_dialog_close_button"
        if self.device.click_element_by_id(popup_id):
             logger.warning("⚠️ Dismissed Popup via ID.")
             popups_dismissed = True
             time.sleep(1)
             
        dismiss_texts = ["No thanks", "Not now", "Skip", "Close", "Got it"]
        for text in dismiss_texts:
             if self.device.click_text(text):
                  logger.warning(f"⚠️ Dismissed Popup via text '{text}'.")
                  popups_dismissed = True
                  time.sleep(1)
                  break
                  
        return popups_dismissed

    def get_post_link(self) -> Optional[str]:
        """
        Retrieves the sharing link for the current post at the top of the feed.
        Returns the URL as a string, or None if failed.
        """
        # Primary strategy: The recorded and analyzed 'Send-Copy' flow
        link = self.get_post_link_via_sharing_sheet()
        if link:
            return link

        # Fallback to legacy context-menu method if necessary (already implemented in some services)
        logger.info("Primary 'Send-Copy' strategy failed. Falling back to context menu...")
        return None

    def get_post_link_via_sharing_sheet(self) -> Optional[str]:
        """
        Implementation of the recorded LinkedIn flow:
        1. Find Send button (semantic anchor + rightmost sibling)
        2. Tap Send -> Opens sharing sheet
        3. Tap 'Copy link' in sheet
        4. Return clipboard content
        """
        logger.info("Attempting Send-Copy flow...")
        
        # 1. Find Send Button using robust sibling discovery
        # We'll use the anchor logic from get_feed_links_adb but adapted for Appium
        send_coords = self._get_send_button_coords()
        if not send_coords:
            logger.error("Could not locate Send button anchor.")
            return None
        
        cx, cy = send_coords
        logger.info(f"Tapping Send button at ({cx}, {cy})")
        self._adb.tap(cx, cy)
        time.sleep(WAIT_SHORT)
        
        # 2. Click 'Copy link' in the share sheet
        # We use the text/desc discovery which was reliable in analysis
        copy_success = False
        for label in ["Copy link", "Copy link to post", "Copy"]:
            if self._tap_by_text_xml(label, timeout=3, exact_match=False):
                copy_success = True
                break
        
        if not copy_success:
            logger.error("Could not find 'Copy link' in sharing sheet.")
            self._adb.press_back() # Dismiss sheet
            return None
        
        # 3. Retrieve from clipboard
        time.sleep(1)
        link = self.get_clipboard_text()
        
        if link and "linkedin.com" in link:
            clean_url = link.split("?")[0]
            logger.info(f"✅ Extracted link via Share Sheet: {clean_url}")
            return clean_url
            
        logger.warning(f"Unexpected clipboard content: {link}")
        return None

    def _get_send_button_coords(self) -> Optional[tuple[int, int]]:
        """Helper to find the Send button coordinates using the Parent-Sibling logic."""
        xml_str = self._adb.get_xml_source()
        if not xml_str: return None
        
        try:
            root = ET.fromstring(xml_str)
            # Strict anchor keywords for the button row
            candidates = []
            anchor_keywords = ["like", "comment", "repost", "share", "send", "reaction", "reacted", "messaging"]
            
            for node in root.iter():
                desc = (node.attrib.get("content-desc") or "")
                text = (node.attrib.get("text") or "")
                
                # Calibration: Use both summaries and button states as anchors
                found = False
                for kw in anchor_keywords:
                    k_low = kw.lower()
                    if k_low in desc.lower() or k_low in text.lower():
                        # Filter out noisy anchors that match keywords but are not button-related
                        # "Followed by X shared connections" or "You both follow Y"
                        if "shared connection" in desc.lower() or "shared connection" in text.lower():
                            continue
                        if "followed by" in desc.lower() or "followed by" in text.lower():
                            continue
                        
                        # Summary nodes can be long, but buttons are short. 
                        # 100 chars is safe for summary nodes like "X and 33 others reacted"
                        if len(desc) < 100 and len(text) < 100:
                            found = True
                            break
                
                if found:
                    bounds = node.attrib.get("bounds", "")
                    match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        # Action buttons are usually in the lower half of the post
                        if y1 > 500: 
                            logger.debug(f"ADB Discovery: Found candidate '{kw}' at ({x1}, {y1}) - desc: '{desc}', text: '{text}'")
                            candidates.append((y1, node))
            
            if not candidates:
                logger.debug("ADB Discovery: No anchor candidates found in XML.")
                return None
            
            logger.info(f"ADB Discovery: {len(candidates)} candidates found. Sorting...")
            # Use the top-most actionable node among results (usually the first post fully on screen)
            candidates.sort(key=lambda x: x[0])
            anchor_node = candidates[0][1]
            y_coord = candidates[0][0]
            logger.info(f"ADB Discovery: Selected anchor at Y={y_coord}")
            
            # Recursive parent search to find a container with multiple siblings (the button row)
            parent_map = {c: p for p in root.iter() for c in p}
            curr = anchor_node
            for _ in range(3): # Look up to 3 levels up
                p = parent_map.get(curr)
                if p is not None:
                    # Check how many siblings we have in this parent
                    siblings = list(p)
                    if len(siblings) >= 3:
                        # This looks like the button row or post container
                        max_x1 = -1
                        target_node = None
                        for s in siblings:
                            b = s.attrib.get("bounds", "")
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
                            if m:
                                x1, y1, x2, y2 = map(int, m.groups())
                                # S25 Ultra: Send button is rightmost, typically X > 1000
                                # Added: Ensure Y is within 400px of the anchor row
                                if x1 > 1000 and abs(y1 - y_coord) < 400 and x1 > max_x1:
                                    max_x1 = x1
                                    target_node = s
                        
                        if target_node:
                            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", target_node.attrib.get("bounds", ""))
                            if m:
                                x1, y1, x2, y2 = map(int, m.groups())
                                return (x1 + x2) // 2, (y1 + y2) // 2
                    curr = p
                else: break
            
            return None
        except Exception as e:
            logger.debug(f"Anchor discovery failed: {e}")
        return None

    def get_feed_links(self, count=5) -> List[str]:
        """
        Scans the feed and extracts links for multiple posts.
        """
        logger.info(f"Scanning feed for {count} post links...")
        links = []
        seen = set()
        
        retries = 0
        while len(links) < count and retries < count * 2:
            link = self.get_post_link()
            if link and link not in seen:
                links.append(link)
                seen.add(link)
                logger.info(f"Progress: {len(links)}/{count}")
            
            # Scroll to next post
            logger.info("Scrolling to next post...")
            self.scroll_down()
            time.sleep(3) # Stabilization wait for new post components to load/render
            retries += 1
        return links
            
    def get_feed_links_adb(self, count: int = 10):
        """
        Extracts post links using pure ADB (no Appium session needed).
        High reliability fallback using improved semantic discovery.
        """
        import xml.etree.ElementTree as ET
        import re
        links = []
        retries = 0
        max_retries = count * 3
        
        while len(links) < count and retries < max_retries:
            logger.info(f"ADB Extraction: Found {len(links)}/{count} links... (Attempt {retries+1})")
            time.sleep(4) 
            
            xml_str = self._adb.get_xml_source()
            if not xml_str:
                logger.warning("ADB: XML source empty. Retrying...")
                self._adb.scroll_up()
                continue
                
            try:
                root = ET.fromstring(xml_str)
            except Exception as e:
                logger.error(f"ADB: XML parse error: {e}")
                self._adb.scroll_up()
                continue

            # 1. Check if Share Sheet is already open
            copy_node = None
            for node in root.iter():
                text = node.attrib.get("text", "").lower()
                desc = node.attrib.get("content-desc", "").lower()
                if "copy link" in text or "copy link" in desc or "copy to clipboard" in text:
                    copy_node = node
                    break
            
            if copy_node:
                logger.info(f"ADB: Share sheet detected (Node: '{copy_node.attrib.get('text') or copy_node.attrib.get('content-desc')}'). Tapping...")
                self._extract_link_from_open_sheet_adb(copy_node, links)
                self._adb.scroll_up()
                continue

            # 2. Use the central coordinate discovery logic
            send_coords = self._get_send_button_coords()
            if send_coords:
                cx, cy = send_coords
                logger.info(f"ADB: Discovery found potential Send button at ({cx}, {cy}). Tapping.")
                self._adb.tap(cx, cy)
                time.sleep(6) # More time for system share sheet
                
                # Check sharing sheet immediately
                xml_sheet = self._adb.get_xml_source()
                if xml_sheet:
                    try:
                        root_sheet = ET.fromstring(xml_sheet)
                        sheet_found = False
                        for node in root_sheet.iter():
                            s_text = node.attrib.get("text", "").lower()
                            s_desc = node.attrib.get("content-desc", "").lower()
                            # Broader match for share sheets (including system ones on S24)
                            if any(k in s_text or k in s_desc for k in ["copy link", "copy to clipboard", "copy text", "copy url"]):
                                logger.info(f"ADB: Share sheet confirmed after tap (Node: '{s_text or s_desc}'). Extracting...")
                                self._extract_link_from_open_sheet_adb(node, links)
                                sheet_found = True
                                break
                        if not sheet_found:
                            logger.warning("ADB: Tap sent but no 'Copy' node found in subsequent XML. (Might be a system icon-only sub-sheet)")
                            # Fallback: Just try to get clipboard anyway in case it auto-copied or user interaction happened
                            self._extract_link_from_open_sheet_adb(None, links)
                    except Exception as e: 
                        logger.error(f"ADB: Sheet XML parse error: {e}")
            else:
                logger.info("ADB: No 'Send' button anchor found on screen.")
            
            # Scroll to next post
            logger.info("ADB: Scrolling to next post...")
            self._adb.scroll_up()
            time.sleep(5) # 5s scroll as requested
            retries += 1
            
        return links

    def _extract_link_from_open_sheet_adb(self, copy_node, links_list):
        """Helper to tap copy and read clipboard. copy_node can be None for fallback."""
        try:
            if copy_node is not None:
                bounds = copy_node.attrib.get("bounds", "")
                m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
                if m:
                    cx, cy = (int(m.group(1)) + int(m.group(3))) // 2, (int(m.group(2)) + int(m.group(4))) // 2
                    logger.debug(f"ADB: Tapping confirmed Copy link at ({cx}, {cy})")
                    self._adb.tap(cx, cy)
                    time.sleep(4) # Increased to 4s for S25 Ultra
            else:
                # S25 Ultra Fallback: Tap a common share-sheet icon location if no text found
                logger.info("ADB: No explicit 'Copy' text node. Trying icon-fallback tap at (200, 2200)...")
                self._adb.tap(200, 2200) 
                time.sleep(4) # Increased to 4s for S25 Ultra

            url = self._adb.get_clipboard()
            if url:
                url = url.strip()
                logger.info(f"ADB: Captured raw clipboard: '{url[:60]}...'")
                # Relaxed URL matching: Any LinkedIn related URL
                if "linkedin.com" in url or "lnkd.in" in url:
                    clean_url = url.split("?")[0]
                    if clean_url not in links_list:
                        logger.info(f"✅ ADB Extracted: {clean_url}")
                        links_list.append(clean_url)
                        return True
                    else:
                        logger.debug(f"ADB: Duplicate link skipped: {clean_url}")
            else:
                logger.warning("ADB: Clipboard returned empty.")
        except Exception as e:
            logger.error(f"ADB: Link extraction failed: {e}")
        return False

    def get_clipboard_text(self) -> Optional[str]:
        """Returns the text currently on the device clipboard."""
        if not self._driver:
            self.start_session()
        try:
            # Try Appium native first
            return self._driver.get_clipboard_text()
        except Exception as e:
            logger.debug(f"Appium clipboard failed, falling back to ADB broadcast: {e}")
            return self._adb.get_clipboard()


    def _tap_by_text_xml(self, target_text: str, timeout: int = 5, exact_match: bool = False) -> bool:
        """
        Appium-native discovery with UiSelector:
        Much faster on S24 when waitForIdleTimeout is calibrated.
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                # 1. Try Text
                sel = f'new UiSelector().text("{target_text}")' if exact_match else f'new UiSelector().textContains("{target_text}")'
                elements = self._driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, sel)
                if elements:
                    elements[0].click()
                    logger.info(f"Tapped text '{target_text}' via Appium.")
                    return True
                
                # 2. Try Description
                sel_desc = f'new UiSelector().description("{target_text}")' if exact_match else f'new UiSelector().descriptionContains("{target_text}")'
                elements_desc = self._driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, sel_desc)
                if elements_desc:
                    elements_desc[0].click()
                    logger.info(f"Tapped desc '{target_text}' via Appium.")
                    return True
                
                time.sleep(1)
            except Exception as e:
                logger.debug(f"appium_discovery_error: {e}")
                time.sleep(1)
        return False
