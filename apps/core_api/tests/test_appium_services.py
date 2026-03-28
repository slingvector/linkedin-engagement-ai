import pytest
from unittest.mock import MagicMock, patch
from app.services.adb_client import ADBClient
from app.services.appium_read_service import AppiumReadService
from appium.webdriver.common.appiumby import AppiumBy

# ─── ADBClient Tests ─────────────────────────────────────────────────────────

@pytest.fixture
def adb_client():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="device", stderr="")
        client = ADBClient(device_udid="test_device")
        return client

def test_adb_run_command_alias(adb_client):
    with patch.object(adb_client, "_run") as mock_run:
        adb_client._run_command(["test", "args"])
        mock_run.assert_called_once_with(["test", "args"], timeout=15)

def test_adb_get_clipboard_requested_method(adb_client):
    with patch.object(adb_client, "_run_command") as mock_run:
        # Mock successful broadcast response
        mock_run.return_value = (0, 'Broadcast completed: result=1, data="https://linkedin.com/posts/123"', "")
        
        link = adb_client.get_clipboard()
        assert link == "https://linkedin.com/posts/123"
        mock_run.assert_any_call(["shell", "am", "broadcast", "-a", "com.android.clipboard.GET_TEXT"], timeout=5)

# ─── AppiumReadService Tests ──────────────────────────────────────────────────

@pytest.fixture
def appium_service():
    AppiumReadService.reset()
    with patch("app.services.adb_client.ADBClient._ensure_connected"):
        svc = AppiumReadService(config={"device_udid": "test_device"})
        svc._driver = MagicMock()
        return svc

def test_service_device_property(appium_service):
    assert appium_service.device == appium_service

def test_click_text(appium_service):
    with patch.object(appium_service, "_tap_by_text_xml") as mock_tap:
        appium_service.click_text("Test Text", timeout=10)
        mock_tap.assert_called_once_with("Test Text", timeout=10, exact_match=False)

def test_click_element_by_id_success(appium_service):
    mock_el = MagicMock()
    appium_service._driver.find_element.return_value = mock_el
    
    result = appium_service.click_element_by_id("some_id")
    
    assert result is True
    appium_service._driver.find_element.assert_called_once_with(AppiumBy.ID, "some_id")
    mock_el.click.assert_called_once()

def test_dismiss_popups(appium_service):
    with patch.object(appium_service, "click_element_by_id") as mock_click_id, \
         patch.object(appium_service, "click_text") as mock_click_text:
        
        mock_click_id.return_value = True
        mock_click_text.return_value = False
        
        result = appium_service.dismiss_popups()
        
        assert result is True
        mock_click_id.assert_called_once_with("com.linkedin.android:id/ad_non_modal_dialog_close_button")

def test_get_post_link_success(appium_service):
    with patch.object(appium_service, "click_text") as mock_click, \
         patch.object(appium_service, "get_clipboard_text") as mock_clip:
        
        mock_click.side_effect = [True, True] # Send, Copy link
        mock_clip.return_value = "https://www.linkedin.com/posts/activity-12345?tracking=XYZ"
        
        link = appium_service.get_post_link()
        
        assert link == "https://www.linkedin.com/posts/activity-12345"
        assert mock_click.call_count == 2

def test_get_feed_links(appium_service):
    with patch.object(appium_service, "get_post_link") as mock_get_link, \
         patch.object(appium_service, "scroll_down") as mock_scroll:
        
        mock_get_link.side_effect = ["link1", "link1", "link2", None, "link3"]
        
        links = appium_service.get_feed_links(count=3)
        
        assert links == ["link1", "link2", "link3"]
        assert mock_get_link.call_count >= 3
        assert mock_scroll.call_count >= 2

def test_get_clipboard_text_starts_session(appium_service):
    appium_service._driver = None # Simulate no driver
    with patch.object(appium_service, "start_session") as mock_start:
        appium_service.get_clipboard_text()
        mock_start.assert_called_once()
