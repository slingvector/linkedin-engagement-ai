"""
ADBClient — LinkedIn-aware ADB shell command wrapper.

Adapted from the Instagram automation project, adjusted for LinkedIn Android app.
Used by AppiumReadService as a fast, reliable fallback for:
  - Device wake / unlock
  - App launch
  - Tap / swipe coordinates
  - Clipboard read-back (to extract copied post URLs)
"""

import os
import subprocess
import time
import re
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class ADBClient:
    """
    Direct ADB shell command wrapper for LinkedIn mobile automation.

    Why: Appium element parsing can be slow or fail on complex LinkedIn layouts.
    ADB commands bypass the UI hierarchy entirely and are much more stable.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ADBClient, cls).__new__(cls)
        return cls._instance

    def __init__(self, device_udid: str = "", adb_executable: str = "adb"):
        # Ensure initialization only happens once
        if hasattr(self, "_initialized") and self._initialized:
            return
            
        self.device_udid = device_udid
        self.adb_executable = adb_executable
        # If udid provided use -s flag, else ADB auto-selects the only connected device
        self._udid_flags = ["-s", device_udid] if device_udid else []
        self._ensure_connected()
        self._initialized = True

    # ── Connection ────────────────────────────────────────────────────────────

    def _ensure_connected(self):
        """If UDID is a TCP/IP address (contains colon), ensure ADB is connected to it."""
        if self.device_udid and ":" in self.device_udid:
            devices = self.list_devices()
            if self.device_udid not in devices:
                logger.info("Attempting to auto-connect to wireless device", device_udid=self.device_udid)
                cmd = [self.adb_executable, "connect", self.device_udid]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if "connected" in result.stdout.lower():
                    logger.info("ADB wirelessly connected", device_udid=self.device_udid)
                else:
                    logger.warning("ADB wireless connection failed", device_udid=self.device_udid, stdout=result.stdout.strip())

    def _run(self, args: list, timeout: int = 15) -> Tuple[int, str, str]:
        """Execute an adb command and return (returncode, stdout, stderr)."""
        cmd = [self.adb_executable] + self._udid_flags + args
        logger.info("adb_run", cmd=" ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            logger.warning("ADB non-zero exit", cmd=" ".join(cmd), exit_code=result.returncode, stderr=result.stderr.strip())
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    def _run_command(self, args: list, timeout: int = 15) -> Tuple[int, str, str]:
        """Alias for _run to support legacy naming."""
        return self._run(args, timeout=timeout)

    def list_devices(self) -> list[str]:
        """Return list of connected device serial numbers."""
        result = subprocess.run(
            [self.adb_executable, "devices"], capture_output=True, text=True, timeout=10
        )
        devices = []
        for line in result.stdout.splitlines()[1:]:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
        return devices

    # ── Screen / Device Control ───────────────────────────────────────────────

    def wake_screen(self):
        """Turn on screen and dismiss lockscreen via keyevent."""
        self._run(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        time.sleep(1.0)
        self._run(["shell", "input", "keyevent", "KEYCODE_MENU"])
        logger.info("Screen woken via ADB.")

    def unlock_device(self, pin: Optional[str] = None):
        """
        Wakes the screen, swipes up to reveal the PIN pad, and enters the PIN.
        If pin is None, reads DEVICE_PIN from the environment.
        """
        self.wake_screen()

        if not pin:
            pin = os.getenv("DEVICE_PIN")

        if pin:
            logger.info("Attempting to unlock device with PIN...")
            # Swipe up to reveal PIN pad (calibrated for S24 Ultra)
            self.swipe(500, 2200, 500, 400, duration_ms=400)
            time.sleep(1.5)
            
            # Enter PIN via keyevents (more robust for lock screens)
            for digit in str(pin):
                key_code = 7 + int(digit) # KEYCODE_0 is 7, KEYCODE_1 is 8, etc.
                self._run_command(["shell", "input", "keyevent", str(key_code)])
                time.sleep(0.1)
                
            time.sleep(0.5)
            self._run_command(["shell", "input", "keyevent", "66"])  # KEYCODE_ENTER
            logger.info("Device unlock command sent.")
        else:
            logger.info("No PIN provided. Assuming device is already unlocked.")

    def press_home(self):
        """Press the Android HOME button."""
        self._run(["shell", "input", "keyevent", "KEYCODE_HOME"])
        logger.info("Home key pressed.")

    def press_back(self):
        """Press the Android BACK button."""
        self._run(["shell", "input", "keyevent", "KEYCODE_BACK"])

    # ── App Management ────────────────────────────────────────────────────────

    def launch_linkedin(self, package: str = "com.linkedin.android"):
        """Launch LinkedIn using Android monkey — most reliable cold-start method."""
        self._run([
            "shell", "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1"
        ])
        logger.info(f"Launched {package} via monkey.")

    def stop_app(self, package: str):
        """Force stop an app to start clean."""
        self._run(["shell", "am", "force-stop", package])
        logger.info(f"Force-stopped {package}.")

    def get_foreground_package(self) -> str:
        """Determines the package name of the application currently in the foreground."""
        _, stdout, _ = self._run(["shell", "dumpsys", "window", "|", "grep", "-E", "'mCurrentFocus|mFocusedApp'"])
        if stdout:
            match = re.search(r"([a-zA-Z0-9._]+)/", stdout)
            if match:
                pkg = match.group(1)
                if " " in pkg:
                    pkg = pkg.split(" ")[-1]
                return pkg

        # Fallback: dumpsys activity recents
        _, stdout, _ = self._run(["shell", "dumpsys", "activity", "recents", "|", "grep", "'Recent #0'"])
        if stdout:
            match = re.search(r"A=([a-zA-Z0-9._]+)", stdout)
            if match:
                return match.group(1)
        return ""

    # ── Input Actions ─────────────────────────────────────────────────────────

    def tap(self, x: int, y: int):
        """Tap at absolute screen coordinates."""
        self._run(["shell", "input", "tap", str(x), str(y)])

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Swipe from (x1,y1) to (x2,y2) over duration_ms milliseconds."""
        self._run(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])

    def scroll_up(self, distance: int = 1500, duration_ms: int = 600):
        """Scroll the feed up (swipe finger upward = content scrolls up = new content appears)."""
        # Swipe from bottom to top
        self.swipe(540, 1800, 540, 1800 - distance, duration_ms)

    def long_press(self, x: int, y: int, duration_ms: int = 1000):
        """Long-press at coordinates to open context menu."""
        self._run([
            "shell", "input", "swipe",
            str(x), str(y), str(x), str(y), str(duration_ms)
        ])

    def input_text(self, text: str):
        """Type text via ADB input — escapes spaces for shell."""
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        self._run(["shell", "input", "text", escaped])

    # ── Clipboard ─────────────────────────────────────────────────────────────

    def get_foreground_user(self) -> str:
        """Determines the user ID of the foreground package."""
        # Use a single string for shell piping to ensure it's executed correctly by adb shell
        _, stdout, _ = self._run(["shell", "dumpsys activity activities | grep mResumedActivity"])
        if stdout:
            # Look for uXX in the output, e.g. u150 or u0
            match = re.search(r"u(\d+)", stdout)
            if match:
                return match.group(1)
        return "0"

    def get_clipboard(self, retries: int = 3) -> str:
        """
        Read the current clipboard text from the device.
        Incorporates Parcel-based retrieval (Method 4) for S25 Ultra / Android 14+.
        """
        detected_user = self.get_foreground_user()
        users_to_try = ["0"]
        if detected_user != "0": users_to_try.append(detected_user)
            
        for attempt in range(retries):
            # Method 1 & 2: Broadcasts (User-specific)
            for user_id in users_to_try:
                _, stdout, _ = self._run_command(["shell", "am", "broadcast", "--user", user_id, "-a", "com.android.clipboard.GET_TEXT"], timeout=5)
                if stdout and "data=" in stdout:
                     m = re.search(r'data="([^"]+)"', stdout)
                     if m: return m.group(1)

                _, stdout, _ = self._run_command(["shell", "am", "broadcast", "--user", user_id, "-a", "clipper.get"], timeout=5)
                if stdout and "data=" in stdout:
                    m = re.search(r'data="([^"]+)"', stdout)
                    if m: return m.group(1)
        
            # Method 3: dumpsys clipboard (filtered for URLs)
            _, stdout, _ = self._run_command(["shell", "dumpsys", "clipboard"], timeout=5)
            if stdout:
                for line in stdout.splitlines():
                    # Samsung often puts URLs in "clip #" or "text=" or just a raw line
                    if "http" in line:
                        url_match = re.search(r"https?://[^\s'\"]+", line)
                        if url_match: 
                            logger.debug(f"Found URL in dumpsys: {url_match.group(0)}")
                            return url_match.group(0)

            # Method 4: Serialized Parcel (service call clipboard 2)
            # Most resilient for Samsung S25 Ultra / Android 14+
            _, stdout, _ = self._run_command(["shell", "service", "call", "clipboard", "2"], timeout=5)
            if stdout:
                logger.debug(f"Raw Parcel output start: {stdout[:100]}...")
                parcel_text = self._parse_clipboard_parcel(stdout)
                if parcel_text:
                    logger.debug(f"Clipboard Method 4 (Parcel) found: {parcel_text[:40]}...")
                    return parcel_text
            
            if attempt < retries - 1:
                time.sleep(1.5)

        logger.debug("get_clipboard: all methods failed or returned empty")
        return ""

    def _parse_clipboard_parcel(self, stdout: str) -> str:
        """Parses the ASCII segment of a 'service call clipboard 2' parcel dump (S25 Ultra)."""
        try:
            segments = []
            for line in stdout.strip().splitlines():
                if "'" in line:
                    parts = line.split("'")
                    if len(parts) >= 2:
                        segments.append(parts[1])
            
            # Remove dots (NULL bytes in UTF-16 dumps)
            text = "".join(segments).replace(".", "")
            
            # Filter for URL
            url_match = re.search(r"https?://[^\s'\"]+", text)
            if url_match: return url_match.group(0)
            return text if len(text) > 5 else ""
        except Exception as e:
            logger.debug(f"Parcel simplified parse error: {e}")
            return ""

    def set_clipboard(self, text: str):
        """Set clipboard text on device via broadcast."""
        safe = text.replace("'", "\\'")
        self._run([
            "shell", "am", "broadcast",
            "-a", "clipper.set",
            "-e", "text", f"'{safe}'"
        ])

    # ── Debug ─────────────────────────────────────────────────────────────────

    def get_screenshot(self, save_path: str = "/tmp/linkedin_screen.png") -> str:
        """Capture screenshot via ADB screencap (faster than Appium's base64 method)."""
        self._run(["shell", "screencap", "-p", "/sdcard/linkedin_screen.png"])
        self._run(["pull", "/sdcard/linkedin_screen.png", save_path])
        return save_path

    def get_xml_source(self) -> str:
        """
        Fast XML dump via ADB uiautomator — much more reliable than Appium page_source
        for large lists/feeds.
        """
        xml_path_on_device = "/sdcard/view.xml"
        local_path = "/tmp/adb_view.xml"
        
        # 1. Dump UI to XML on device (15s for S24 Ultra performance)
        self._run(["shell", "uiautomator", "dump", xml_path_on_device], timeout=15)
        
        # 2. Pull to local machine
        self._run(["pull", xml_path_on_device, local_path], timeout=10)
        
        # 3. Read and return
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
